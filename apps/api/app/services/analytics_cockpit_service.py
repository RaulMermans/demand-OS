"""
AnalyticsCockpitService — Sprint 16.

Read-only analytics layer. Computes KPIs, trends, risk drivers, reorder queue,
and executive summary from existing pipeline tables. Never writes to the DB.

All values are derived from real pipeline outputs. No hardcoded metrics.
No fake confidence scores. No external side effects.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    RawProduct, RawStore, RawOrder, RawInventorySnapshot,
    InventoryDaily, SalesDaily, Forecast, ForecastRun,
    StockoutRisk, StockoutRiskRun,
    ReorderRecommendation, RecommendationRun,
    ModelVersion, ModelMetric, FeatureMatrix,
)
from app.schemas.analytics import (
    CockpitResponse, DatasetKpis, InventoryKpis, ForecastingKpis,
    RiskKpis, RecommendationKpis, PipelineStatus,
    InventoryTrendResponse, InventoryTrendPoint, InventoryTrendMetadata,
    RiskDriversResponse, RiskDriverEntry, RiskDriver,
    ReorderQueueResponse, ReorderQueueItem,
    ExecutiveSummaryResponse,
)

logger = logging.getLogger(__name__)

# WAPE quality thresholds (same as data_science_summary_service)
_WAPE_STRONG = 0.30
_WAPE_DIRECTIONAL = 0.60


def _wape_quality_label(wape: Optional[float]) -> str:
    if wape is None:
        return "No model"
    if wape <= _WAPE_STRONG:
        return "Strong"
    if wape <= _WAPE_DIRECTIONAL:
        return "Directional"
    return "Weak / Demo signal"


def _wape_interpretation(wape: Optional[float], model_name: Optional[str]) -> str:
    label = _wape_quality_label(wape)
    name = model_name or "Model"
    if label == "No model":
        return "No forecast model has been trained yet."
    if label == "Strong":
        return f"{name} provides a strong demand signal for inventory planning on this synthetic dataset."
    if label == "Directional":
        return (
            f"{name} provides a directional planning signal for this synthetic demo dataset. "
            "Use forecasts to guide inventory decisions, not as exact predictions."
        )
    return (
        f"{name} provides a demonstration signal on this synthetic dataset. "
        "Forecasts indicate demand direction but point estimates carry meaningful uncertainty."
    )


def _ready_or_pending(flag: bool) -> str:
    return "ready" if flag else "pending"


def _urgency_rank(urgency: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(urgency, 4)


def _confidence_label(rec: ReorderRecommendation) -> str:
    """Map recommendation fields to a qualitative confidence label."""
    if rec.urgency in ("critical", "high") and rec.risk_tier in ("critical", "high"):
        return "review_now"
    if rec.urgency == "medium" or rec.risk_tier in ("medium", "high"):
        return "monitor"
    return "low_priority"


def _driver_severity(days_until_stockout: Optional[float], lead_time: Optional[int]) -> str:
    if days_until_stockout is not None and days_until_stockout <= 7:
        return "high"
    if lead_time and days_until_stockout is not None and days_until_stockout <= lead_time:
        return "high"
    return "medium"


class AnalyticsCockpitService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Cockpit summary
    # ------------------------------------------------------------------

    def get_cockpit(self) -> CockpitResponse:
        db = self.db

        # --- Dataset counts ---
        products = db.query(func.count(RawProduct.id)).scalar() or 0
        stores = db.query(func.count(RawStore.id)).scalar() or 0
        orders = db.query(func.count(RawOrder.id)).scalar() or 0
        inv_snapshots = db.query(func.count(RawInventorySnapshot.id)).scalar() or 0

        # SKU-store combinations from latest risk run (most accurate) or product × store
        risk_combo_count = (
            db.query(func.count(func.distinct(func.concat(StockoutRisk.product_id, "-", StockoutRisk.store_id))))
            .scalar() or 0
        )
        sku_store_combinations = risk_combo_count if risk_combo_count > 0 else products * stores

        # --- Inventory KPIs ---
        # Latest on_hand per (product, store) from inventory_daily
        latest_inv_subq = (
            db.query(
                InventoryDaily.product_id,
                InventoryDaily.store_id,
                func.max(InventoryDaily.date).label("max_date"),
            )
            .group_by(InventoryDaily.product_id, InventoryDaily.store_id)
            .subquery()
        )
        inv_rows = (
            db.query(InventoryDaily)
            .join(
                latest_inv_subq,
                (InventoryDaily.product_id == latest_inv_subq.c.product_id)
                & (InventoryDaily.store_id == latest_inv_subq.c.store_id)
                & (InventoryDaily.date == latest_inv_subq.c.max_date),
            )
            .all()
        )

        total_inv_units: Optional[float] = None
        est_inv_value: Optional[float] = None
        inv_value_method = "unit_cost"

        if inv_rows:
            # Build a product_id → (unit_cost, unit_price) lookup
            products_raw = db.query(RawProduct).all()
            cost_map: dict[str, Optional[float]] = {p.id: p.unit_cost for p in products_raw}
            price_map: dict[str, Optional[float]] = {p.id: p.unit_price for p in products_raw}

            total_inv_units = sum(r.on_hand_units for r in inv_rows if r.on_hand_units is not None)
            est_inv_value = 0.0
            used_fallback = False
            for r in inv_rows:
                units = r.on_hand_units or 0.0
                cost = cost_map.get(r.product_id)
                price = price_map.get(r.product_id)
                if cost is not None and cost > 0:
                    est_inv_value += units * cost
                elif price is not None and price > 0:
                    est_inv_value += units * price
                    used_fallback = True
                # else: 0 contribution
            if used_fallback:
                inv_value_method = "unit_price (fallback)"

        # --- Stockout risk KPIs from latest risk run ---
        latest_risk_run = (
            db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.completed_at.desc())
            .first()
        )

        critical_count = high_count = medium_count = low_count = 0
        est_lost_sales: Optional[float] = None
        at_risk = 0
        stockout_risk_pct: Optional[float] = None

        if latest_risk_run:
            risks = (
                db.query(StockoutRisk)
                .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
                .all()
            )
            for r in risks:
                if r.risk_tier == "critical":
                    critical_count += 1
                elif r.risk_tier == "high":
                    high_count += 1
                elif r.risk_tier == "medium":
                    medium_count += 1
                elif r.risk_tier == "low":
                    low_count += 1

            total_risk_rows = len(risks)
            at_risk = critical_count + high_count
            if total_risk_rows > 0:
                stockout_risk_pct = round(at_risk / total_risk_rows * 100, 1)

            est_lost_sales = sum(
                (r.lost_sales_value_estimate or 0.0) for r in risks
            )
            if est_lost_sales == 0:
                est_lost_sales = None

        # --- Forecasting KPIs ---
        latest_forecast_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.status == "completed")
            .order_by(ForecastRun.completed_at.desc())
            .first()
        )

        latest_model_name: Optional[str] = None
        latest_wape: Optional[float] = None
        forecast_rows = 0

        if latest_forecast_run:
            latest_model_name = latest_forecast_run.model_name
            forecast_rows = latest_forecast_run.rows_created or 0

            # WAPE from model metrics (level="overall", level_value="all")
            metric = (
                db.query(ModelMetric)
                .filter(
                    ModelMetric.run_id == latest_forecast_run.id,
                    ModelMetric.level == "overall",
                )
                .first()
            )
            if metric is not None:
                latest_wape = metric.wape

        quality_label = _wape_quality_label(latest_wape)
        interpretation = _wape_interpretation(latest_wape, latest_model_name)

        # --- Recommendation KPIs ---
        latest_rec_run = (
            db.query(RecommendationRun)
            .filter(RecommendationRun.status == "completed")
            .order_by(RecommendationRun.completed_at.desc())
            .first()
        )

        open_recs = 0
        est_order_cost: Optional[float] = None
        est_lost_sales_addressed: Optional[float] = None

        if latest_rec_run:
            recs = (
                db.query(ReorderRecommendation)
                .filter(
                    ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                    ReorderRecommendation.status == "open",
                )
                .all()
            )
            open_recs = len(recs)
            if recs:
                est_order_cost = sum(r.estimated_order_cost or 0.0 for r in recs) or None
                est_lost_sales_addressed = sum(r.estimated_lost_sales_avoided or 0.0 for r in recs) or None

        # --- Pipeline status ---
        pipeline = PipelineStatus(
            data_seeded=_ready_or_pending(products > 0),
            features=_ready_or_pending(
                (db.query(func.count(FeatureMatrix.id)).scalar() or 0) > 0
            ),
            forecasts=_ready_or_pending(latest_forecast_run is not None),
            risks=_ready_or_pending(latest_risk_run is not None),
            recommendations=_ready_or_pending(latest_rec_run is not None),
        )

        return CockpitResponse(
            status="ready" if products > 0 else "no_data",
            generated_at=datetime.utcnow(),
            dataset=DatasetKpis(
                products=products,
                stores=stores,
                sku_store_combinations=sku_store_combinations,
                orders=orders,
                inventory_snapshots=inv_snapshots,
            ),
            inventory=InventoryKpis(
                total_inventory_units=total_inv_units,
                estimated_inventory_value=round(est_inv_value, 2) if est_inv_value is not None else None,
                inventory_value_method=inv_value_method,
                stockout_risk_percent=stockout_risk_pct,
                at_risk_sku_stores=at_risk,
            ),
            forecasting=ForecastingKpis(
                latest_model=latest_model_name,
                latest_wape=round(latest_wape, 4) if latest_wape is not None else None,
                forecast_quality_label=quality_label,
                forecast_rows=forecast_rows,
                interpretation=interpretation,
            ),
            risk=RiskKpis(
                critical=critical_count,
                high=high_count,
                medium=medium_count,
                low=low_count,
                estimated_lost_sales=round(est_lost_sales, 2) if est_lost_sales is not None else None,
            ),
            recommendations=RecommendationKpis(
                open=open_recs,
                estimated_order_cost=round(est_order_cost, 2) if est_order_cost is not None else None,
                estimated_lost_sales_addressed=(
                    round(est_lost_sales_addressed, 2) if est_lost_sales_addressed is not None else None
                ),
            ),
            pipeline=pipeline,
        )

    # ------------------------------------------------------------------
    # Inventory trend
    # ------------------------------------------------------------------

    def get_inventory_trend(
        self,
        product_id: Optional[str],
        store_id: Optional[str],
        days: int,
    ) -> InventoryTrendResponse:
        db = self.db
        cutoff = date.today() - timedelta(days=days)

        # Determine mode
        mode = "aggregate" if (product_id is None and store_id is None) else "filtered"

        # --- Inventory daily ---
        inv_q = db.query(InventoryDaily).filter(InventoryDaily.date >= cutoff)
        if product_id:
            inv_q = inv_q.filter(InventoryDaily.product_id == product_id)
        if store_id:
            inv_q = inv_q.filter(InventoryDaily.store_id == store_id)
        inv_rows = inv_q.order_by(InventoryDaily.date).all()

        # Aggregate by date
        inv_by_date: dict[date, float] = {}
        for r in inv_rows:
            d = r.date
            inv_by_date[d] = inv_by_date.get(d, 0.0) + (r.on_hand_units or 0.0)

        # --- Forecast demand (forward_planning run preferred) ---
        fcast_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.status == "completed")
            .order_by(
                # Prefer forward_planning, then any completed
                ForecastRun.completed_at.desc()
            )
            .first()
        )

        forecast_by_date: dict[date, float] = {}
        if fcast_run:
            fcast_q = (
                db.query(Forecast)
                .filter(
                    Forecast.forecast_run_id == fcast_run.id,
                    Forecast.forecast_date >= cutoff,
                )
            )
            if product_id:
                fcast_q = fcast_q.filter(Forecast.product_id == product_id)
            if store_id:
                fcast_q = fcast_q.filter(Forecast.store_id == store_id)
            for r in fcast_q.all():
                d = r.forecast_date
                forecast_by_date[d] = forecast_by_date.get(d, 0.0) + (r.p50_units or 0.0)

        # --- Reorder point and safety stock from latest risk run ---
        reorder_point: Optional[float] = None
        safety_stock: Optional[float] = None
        reorder_note: Optional[str] = None

        latest_risk_run = (
            db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.completed_at.desc())
            .first()
        )
        if latest_risk_run:
            risk_q = db.query(StockoutRisk).filter(
                StockoutRisk.risk_run_id == latest_risk_run.id
            )
            if product_id:
                risk_q = risk_q.filter(StockoutRisk.product_id == product_id)
            if store_id:
                risk_q = risk_q.filter(StockoutRisk.store_id == store_id)
            risk_rows = risk_q.all()

            # Latest rec run for reorder_point_units
            latest_rec_run = (
                db.query(RecommendationRun)
                .filter(RecommendationRun.status == "completed")
                .order_by(RecommendationRun.completed_at.desc())
                .first()
            )
            if latest_rec_run:
                rec_q = db.query(ReorderRecommendation).filter(
                    ReorderRecommendation.recommendation_run_id == latest_rec_run.id
                )
                if product_id:
                    rec_q = rec_q.filter(ReorderRecommendation.product_id == product_id)
                if store_id:
                    rec_q = rec_q.filter(ReorderRecommendation.store_id == store_id)
                rec_rows = rec_q.all()
                if rec_rows:
                    reorder_point_vals = [r.reorder_point_units for r in rec_rows if r.reorder_point_units is not None]
                    safety_stock_vals = [r.safety_stock_units for r in rec_rows if r.safety_stock_units is not None]
                    if reorder_point_vals:
                        reorder_point = round(sum(reorder_point_vals) / len(reorder_point_vals), 1)
                    if safety_stock_vals:
                        safety_stock = round(sum(safety_stock_vals) / len(safety_stock_vals), 1)
                    if mode == "aggregate":
                        reorder_note = (
                            "Reorder point and safety stock shown are the average across all product/store "
                            "combinations. Filter by product and store for specific values."
                        )
                    else:
                        reorder_note = (
                            "Reorder point and safety stock are the latest computed values, "
                            "shown as flat reference lines for the trend window."
                        )

        # Build series over all known dates in the window
        all_dates = sorted(set(list(inv_by_date.keys()) + list(forecast_by_date.keys())))
        if not all_dates:
            # Generate placeholder date range
            all_dates = [date.today() - timedelta(days=days - i) for i in range(days + 1)]

        series = [
            InventoryTrendPoint(
                date=d,
                inventory_on_hand=round(inv_by_date[d], 1) if d in inv_by_date else None,
                forecasted_demand=round(forecast_by_date[d], 1) if d in forecast_by_date else None,
                reorder_point=reorder_point,
                safety_stock=safety_stock,
            )
            for d in all_dates
        ]

        return InventoryTrendResponse(
            series=series,
            metadata=InventoryTrendMetadata(
                product_id=product_id,
                store_id=store_id,
                days=days,
                mode=mode,
                reorder_point_note=reorder_note,
            ),
        )

    # ------------------------------------------------------------------
    # Risk drivers
    # ------------------------------------------------------------------

    def get_risk_drivers(self, limit: int = 10) -> RiskDriversResponse:
        db = self.db

        latest_risk_run = (
            db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.completed_at.desc())
            .first()
        )
        if not latest_risk_run:
            return RiskDriversResponse(
                drivers=[],
                total=0,
                disclaimer=(
                    "No completed risk run found. Run the stockout risk pipeline to see risk drivers."
                ),
            )

        # Load risks ordered by tier and lost sales
        tier_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
        risks = (
            db.query(StockoutRisk)
            .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
            .all()
        )
        risks.sort(
            key=lambda r: (
                tier_order.get(r.risk_tier or "unknown", 4),
                -(r.lost_sales_value_estimate or 0.0),
            )
        )
        risks = risks[:limit]

        # Product name lookup
        products = db.query(RawProduct).all()
        name_map = {p.id: p.name for p in products}
        sku_map = {p.id: p.sku for p in products}

        entries: list[RiskDriverEntry] = []
        for r in risks:
            drivers: list[RiskDriver] = []

            # Inventory below reorder point
            latest_rec_run = (
                db.query(RecommendationRun)
                .filter(RecommendationRun.status == "completed")
                .order_by(RecommendationRun.completed_at.desc())
                .first()
            )
            reorder_pt: Optional[float] = None
            if latest_rec_run:
                rec = (
                    db.query(ReorderRecommendation)
                    .filter(
                        ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                        ReorderRecommendation.product_id == r.product_id,
                        ReorderRecommendation.store_id == r.store_id,
                    )
                    .first()
                )
                if rec:
                    reorder_pt = rec.reorder_point_units

            avail = r.current_available_units
            if reorder_pt is not None and avail is not None and avail < reorder_pt:
                drivers.append(RiskDriver(
                    name="Inventory below reorder point",
                    severity="high",
                    explanation=(
                        f"Available inventory ({avail:.0f} units) is below the computed "
                        f"reorder point ({reorder_pt:.0f} units), contributing to elevated risk."
                    ),
                ))

            # Short stockout horizon
            days_out = r.days_until_stockout
            if days_out is not None and days_out <= 7:
                drivers.append(RiskDriver(
                    name="Short stockout horizon",
                    severity="high",
                    explanation=(
                        f"Projected days until stockout is {days_out:.1f} days — "
                        "within a 7-day critical threshold."
                    ),
                ))
            elif days_out is not None and days_out <= 14:
                drivers.append(RiskDriver(
                    name="Short stockout horizon",
                    severity="medium",
                    explanation=(
                        f"Projected days until stockout is {days_out:.1f} days — "
                        "below the 14-day monitoring threshold."
                    ),
                ))

            # High forecast demand
            if r.forecast_demand_p50 is not None and r.average_daily_forecast is not None:
                if r.average_daily_forecast > 0 and avail is not None:
                    coverage_days = avail / r.average_daily_forecast
                    if coverage_days < (r.supplier_lead_time_days or 14):
                        drivers.append(RiskDriver(
                            name="High forecast demand relative to stock",
                            severity="high" if coverage_days < 7 else "medium",
                            explanation=(
                                f"Forecasted average daily demand ({r.average_daily_forecast:.1f} units/day) "
                                f"gives only {coverage_days:.1f} days of inventory coverage, "
                                "which is associated with higher stockout exposure."
                            ),
                        ))

            # Long supplier lead time
            lead = r.supplier_lead_time_days
            if lead is not None and lead > 14:
                drivers.append(RiskDriver(
                    name="Long supplier lead time",
                    severity="medium" if lead <= 21 else "high",
                    explanation=(
                        f"Supplier lead time is {lead} days, which reduces the replenishment window "
                        "and contributes to higher inventory risk."
                    ),
                ))

            # Low supplier reliability
            rel = r.supplier_reliability_score
            if rel is not None and rel < 0.7:
                drivers.append(RiskDriver(
                    name="Low supplier reliability",
                    severity="medium" if rel >= 0.5 else "high",
                    explanation=(
                        f"Supplier reliability score is {rel:.2f} (below 0.70), "
                        "which is associated with higher delivery uncertainty."
                    ),
                ))

            # High lost sales exposure
            lsv = r.lost_sales_value_estimate
            if lsv is not None and lsv > 500:
                drivers.append(RiskDriver(
                    name="High lost sales exposure",
                    severity="high" if lsv > 2000 else "medium",
                    explanation=(
                        f"Estimated lost sales exposure is €{lsv:,.0f}, "
                        "indicating a meaningful revenue risk if not addressed."
                    ),
                ))

            # Low inventory coverage
            cov = r.inventory_coverage_ratio
            if cov is not None and cov < 1.0:
                drivers.append(RiskDriver(
                    name="Low inventory coverage",
                    severity="high",
                    explanation=(
                        f"Inventory coverage ratio is {cov:.2f} — below 1.0 means current stock "
                        "is projected to be insufficient to cover forecast demand."
                    ),
                ))

            if not drivers:
                drivers.append(RiskDriver(
                    name="General elevated risk",
                    severity="medium" if r.risk_tier in ("medium", "low") else "high",
                    explanation=r.risk_reason or "Risk tier is elevated based on combined inventory and forecast signals.",
                ))

            entries.append(RiskDriverEntry(
                product_id=r.product_id,
                store_id=r.store_id,
                product_name=name_map.get(r.product_id),
                sku=sku_map.get(r.product_id),
                risk_tier=r.risk_tier or "unknown",
                risk_score=r.risk_score,
                estimated_lost_sales=round(r.lost_sales_value_estimate, 2) if r.lost_sales_value_estimate else None,
                drivers=drivers,
            ))

        return RiskDriversResponse(
            drivers=entries,
            total=len(entries),
            disclaimer=(
                "Risk drivers are rule-based explanations derived from inventory, forecast, "
                "and supplier data. They indicate contributing factors, not guaranteed causal relationships."
            ),
        )

    # ------------------------------------------------------------------
    # Reorder queue
    # ------------------------------------------------------------------

    def get_reorder_queue(self) -> ReorderQueueResponse:
        db = self.db

        latest_rec_run = (
            db.query(RecommendationRun)
            .filter(RecommendationRun.status == "completed")
            .order_by(RecommendationRun.completed_at.desc())
            .first()
        )
        if not latest_rec_run:
            return ReorderQueueResponse(
                items=[],
                total=0,
                safety_note=(
                    "DemandOS does not create purchase orders or contact suppliers. "
                    "Recommendations are internal review guidance only."
                ),
            )

        recs = (
            db.query(ReorderRecommendation)
            .filter(
                ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                ReorderRecommendation.status == "open",
            )
            .all()
        )

        # Sort: urgency → risk tier → lost sales desc → order cost desc
        tier_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
        recs.sort(key=lambda r: (
            _urgency_rank(r.urgency or "low"),
            tier_rank.get(r.risk_tier or "unknown", 4),
            -(r.estimated_lost_sales_value or 0.0),
            -(r.estimated_order_cost or 0.0),
        ))

        # Product name / sku lookup
        products = db.query(RawProduct).all()
        name_map = {p.id: p.name for p in products}
        sku_map = {p.id: p.sku for p in products}
        category_map = {p.id: p.category for p in products}

        items: list[ReorderQueueItem] = []
        for rec in recs:
            prod_name = name_map.get(rec.product_id)
            sku = sku_map.get(rec.product_id)
            category = category_map.get(rec.product_id) or rec.category
            confidence_label = _confidence_label(rec)

            # Reason: use stored recommendation_reason or construct one
            reason = rec.recommendation_reason
            if not reason:
                parts = []
                if rec.risk_tier in ("critical", "high"):
                    parts.append(f"Risk tier is {rec.risk_tier}.")
                if rec.days_until_stockout is not None:
                    parts.append(f"Estimated {rec.days_until_stockout:.0f} days until stockout.")
                if rec.estimated_lost_sales_value:
                    parts.append(f"Lost sales exposure: €{rec.estimated_lost_sales_value:,.0f}.")
                reason = " ".join(parts) if parts else "Inventory is below the computed reorder point."

            items.append(ReorderQueueItem(
                recommendation_id=rec.id,
                product_id=rec.product_id,
                store_id=rec.store_id,
                sku=sku,
                product_name=prod_name,
                category=category,
                risk_tier=rec.risk_tier,
                recommended_units=rec.recommended_units_rounded,
                estimated_order_cost=round(rec.estimated_order_cost, 2) if rec.estimated_order_cost else None,
                lead_time_days=rec.supplier_lead_time_days,
                urgency=rec.urgency or "low",
                confidence_label=confidence_label,
                reason=reason,
                status=rec.status or "open",
            ))

        return ReorderQueueResponse(
            items=items,
            total=len(items),
            safety_note=(
                "DemandOS does not create purchase orders or contact suppliers. "
                "Recommendations are internal review guidance only."
            ),
        )

    # ------------------------------------------------------------------
    # Executive summary
    # ------------------------------------------------------------------

    def get_executive_summary(self) -> ExecutiveSummaryResponse:
        db = self.db

        cockpit = self.get_cockpit()
        risk = cockpit.risk
        recs = cockpit.recommendations
        inv = cockpit.inventory
        fcst = cockpit.forecasting

        at_risk = risk.critical + risk.high
        headline = (
            f"{at_risk} product-store combination{'s' if at_risk != 1 else ''} require review."
            if at_risk > 0
            else "No critical or high-risk product-store combinations currently flagged."
        )

        summary: list[str] = []

        if risk.critical > 0 or risk.high > 0:
            summary.append(
                f"{risk.critical} critical and {risk.high} high-risk product-store "
                f"combination{'s are' if (risk.critical + risk.high) != 1 else ' is'} currently flagged."
            )
        else:
            summary.append("No critical or high-risk product-store combinations are currently flagged.")

        if risk.estimated_lost_sales is not None:
            summary.append(
                f"Estimated lost sales exposure is €{risk.estimated_lost_sales:,.0f}."
            )

        if recs.open > 0:
            summary.append(
                f"{recs.open} open reorder recommendation{'s are' if recs.open != 1 else ' is'} "
                "available for internal review."
            )

        summary.append(
            f"Forecast quality is {fcst.forecast_quality_label.lower()}; "
            "use recommendations as planning guidance, not automated purchase orders."
        )

        if inv.stockout_risk_percent is not None:
            summary.append(
                f"{inv.stockout_risk_percent:.1f}% of tracked product-store combinations "
                "carry critical or high stockout risk."
            )

        next_actions: list[str] = []
        if risk.critical > 0:
            next_actions.append("Review critical risks first — these carry the highest stockout exposure.")
        if risk.high > 0:
            next_actions.append("Inspect high-risk items and their open reorder recommendations.")
        if recs.open > 0:
            next_actions.append(
                f"Review {recs.open} open reorder recommendation{'s' if recs.open != 1 else ''} "
                "before committing to any procurement decisions."
            )
        next_actions.append("Use scenario planning before changing inventory policy.")

        return ExecutiveSummaryResponse(
            headline=headline,
            summary=summary,
            next_actions=next_actions,
            safety_note=(
                "DemandOS does not create purchase orders or contact suppliers. "
                "All outputs are internal review guidance for synthetic demo data."
            ),
        )
