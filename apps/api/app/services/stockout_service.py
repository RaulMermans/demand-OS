"""
StockoutService — computes stockout risk scores from forecasts + inventory.

Sprint 6: Full implementation.

Pipeline:
  forecast_runs (forward_planning or backtest)
    + inventory_daily  (current on-hand per product/store)
    + raw_purchase_orders  (inbound stock within horizon)
    + raw_suppliers / raw_products  (lead times, prices, supplier reliability)
    → StockoutService.run_stockout_risk()
    → stockout_risks table  (one row per risk_run × product × store)
    → stockout_risk_runs table  (audit record)

Modes
-----
forward_planning:
  Uses a completed forward-planning forecast run (backtest_mode=False, mode=forward_planning).
  Risk is calculated relative to the latest available inventory_daily date ("as_of_date").
  Preferred mode — represents actual operational risk.

historical_simulation:
  Uses a completed backtest forecast run.
  Risk is calculated relative to the backtest start date.
  Clearly marked as simulation, NOT operational risk.

Forecast run selection (when forecast_run_id not provided):
  1. Latest completed forward-planning run
  2. Latest completed backtest run (historical_simulation mode)
  3. Error: "No usable forecast run found."

Key formulas (all deterministic, no LLM)
-----------------------------------------
current_available_units     = on_hand_units  (reserved_units not separately tracked in inventory_daily)
inbound_units_within_horizon = sum(PO.quantity_ordered where expected_delivery_date in horizon
                                   and status in submitted/confirmed)
forecast_demand_p50          = sum(p50_units for dates in horizon)
forecast_demand_p90          = sum(p90_units for dates in horizon)  — falls back to p50 when null
average_daily_forecast       = forecast_demand_p50 / horizon_days
projected_end_inventory_p50  = available + inbound - forecast_demand_p50
projected_end_inventory_p90  = available + inbound - forecast_demand_p90
days_of_supply               = available / average_daily_forecast   (null when avg==0)
days_until_stockout          = (available + inbound) / average_daily_forecast  when proj_p50 < 0
safety_stock_units           = 1.65 * demand_std_daily * sqrt(lead_time_days)
  demand_std_daily           = last rolling_units_std_7d from feature_matrix; fallback 0
inventory_coverage_ratio     = (available + inbound) / max(forecast_demand_p50, 1)
lost_sales_units_estimate    = max(0, forecast_demand_p50 - available - inbound)
lost_sales_value_estimate    = lost_sales_units_estimate * retail_price

Risk tier rules (deterministic):
  critical : days_until_stockout is not null AND <= min(7, supplier_lead_time_days)
  high     : projected_end_inventory_p50 < 0 OR inventory_coverage_ratio < 1.0
  medium   : projected_end_inventory_p90 < safety_stock_units OR coverage_ratio < 1.25
  low      : projected_end_inventory_p90 >= safety_stock_units AND coverage_ratio >= 1.25
  unknown  : missing forecast, inventory, or supplier data

Risk score (0–100, higher = worse risk):
  critical → base 95
  high     → base 75
  medium   → base 45
  low      → base 15
  unknown  → null
  Adjusted by supplier reliability (low reliability → +5) and lost sales magnitude.

Idempotency: clears previous rows for the same (mode, horizon_days, as_of_date) before reinserting.

Reference: Inventory optimization literature — safety stock (Brown 1959), service-level
planning (Silver, Pyke, Thomas 2017). No reorder quantities are computed here (Sprint 7).
"""

import logging
import math
import uuid
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    ForecastRun, Forecast, FeatureMatrix,
    InventoryDaily, RawPurchaseOrder, RawProduct, RawSupplier,
    StockoutRiskRun, StockoutRisk,
)

logger = logging.getLogger(__name__)

# 95th-percentile z-score for service-level safety stock
_Z_SCORE = 1.65

# PO statuses considered "inbound" (ordered but not yet in inventory)
_INBOUND_PO_STATUSES = {"submitted", "confirmed"}

# Risk score bases per tier
_TIER_BASE_SCORE = {
    "critical": 95.0,
    "high": 75.0,
    "medium": 45.0,
    "low": 15.0,
    "unknown": None,
}

VALID_MODES = {"forward_planning", "historical_simulation"}


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class StockoutRiskResult:
    def __init__(
        self,
        risk_run_id: str,
        forecast_run_id: str,
        mode: str,
        horizon_days: int,
        rows_created: int,
        risk_counts: dict,
        as_of_date: date,
        status: str = "completed",
        error: Optional[str] = None,
    ):
        self.risk_run_id = risk_run_id
        self.forecast_run_id = forecast_run_id
        self.mode = mode
        self.horizon_days = horizon_days
        self.rows_created = rows_created
        self.risk_counts = risk_counts
        self.as_of_date = as_of_date
        self.status = status
        self.error = error


class StockoutService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_stockout_risk(
        self,
        forecast_run_id: Optional[str] = None,
        horizon_days: int = 28,
        mode: str = "forward_planning",
    ) -> dict:
        """
        Run the stockout risk engine.

        Selects the best available forecast run, reads current inventory,
        inbound POs, and supplier data, then computes risk metrics and
        persists results to stockout_risk_runs and stockout_risks.

        Returns a dict summary suitable for API response serialization.
        """
        if mode not in VALID_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of {sorted(VALID_MODES)}"
            )

        run_id = f"risk-run-{uuid.uuid4()}"
        risk_run = StockoutRiskRun(
            id=run_id,
            mode=mode,
            status="running",
            started_at=datetime.utcnow(),
            risk_horizon_days=horizon_days,
            config_json={"requested_forecast_run_id": forecast_run_id, "horizon_days": horizon_days},
        )
        self.db.add(risk_run)
        self.db.flush()

        try:
            # 1. Select forecast run
            frun = self._select_forecast_run(forecast_run_id, mode)
            if frun is None:
                risk_run.status = "failed"
                risk_run.error_message = (
                    "No usable forecast run found. "
                    "Run POST /api/forecasts/baseline/run or POST /api/forecasts/planning/run first."
                )
                risk_run.completed_at = datetime.utcnow()
                self.db.commit()
                return {
                    "status": "failed",
                    "risk_run_id": run_id,
                    "error": risk_run.error_message,
                }

            effective_mode = mode
            if frun.mode == "backtest" and mode == "forward_planning":
                effective_mode = "historical_simulation"
                logger.warning(
                    "No forward_planning forecast found. Falling back to historical_simulation."
                )

            # 2. Determine as_of_date
            as_of_date = self._resolve_as_of_date(frun, effective_mode)
            risk_run.as_of_date = as_of_date
            risk_run.source_forecast_run_id = frun.id
            if frun.model_version_id:
                risk_run.source_model_version_id = frun.model_version_id
            self.db.flush()

            # 3–6. Load supporting data
            inventory_map = self._load_current_inventory(as_of_date)
            inbound_map = self._load_inbound_pos(as_of_date, horizon_days)
            product_map = self._load_product_info()
            supplier_map = self._load_supplier_info()
            std_map = self._load_demand_std()

            # 7. Load forecast rows
            forecast_rows = self._load_forecast_rows(frun, as_of_date, horizon_days, effective_mode)
            if not forecast_rows:
                risk_run.status = "failed"
                risk_run.error_message = (
                    f"No forecast rows found for run {frun.id} within horizon "
                    f"[{as_of_date} + {horizon_days} days]."
                )
                risk_run.completed_at = datetime.utcnow()
                self.db.commit()
                return {
                    "status": "failed",
                    "risk_run_id": run_id,
                    "error": risk_run.error_message,
                }

            # 8. Idempotency: clear previous runs with same parameters
            self._clear_previous_runs(
                mode=effective_mode,
                horizon_days=horizon_days,
                as_of_date=as_of_date,
                current_run_id=run_id,
            )

            # 9. Compute risk rows per (product, store)
            risk_rows, tier_counts = self._compute_risk_rows(
                forecast_rows=forecast_rows,
                inventory_map=inventory_map,
                inbound_map=inbound_map,
                product_map=product_map,
                supplier_map=supplier_map,
                std_map=std_map,
                risk_run_id=run_id,
                as_of_date=as_of_date,
                horizon_days=horizon_days,
                frun=frun,
            )

            # 10. Persist risk rows
            self.db.bulk_insert_mappings(StockoutRisk, risk_rows)
            self.db.flush()

            # 11. Update run record
            risk_run.status = "completed"
            risk_run.completed_at = datetime.utcnow()
            risk_run.mode = effective_mode
            risk_run.rows_created = len(risk_rows)
            risk_run.critical_count = tier_counts.get("critical", 0)
            risk_run.high_count = tier_counts.get("high", 0)
            risk_run.medium_count = tier_counts.get("medium", 0)
            risk_run.low_count = tier_counts.get("low", 0)
            risk_run.unknown_count = tier_counts.get("unknown", 0)
            risk_run.checks_json = self._build_checks(
                len(risk_rows), tier_counts, inventory_map, inbound_map
            )
            self.db.commit()

            return {
                "status": "completed",
                "risk_run_id": run_id,
                "forecast_run_id": frun.id,
                "mode": effective_mode,
                "horizon_days": horizon_days,
                "as_of_date": str(as_of_date),
                "rows_created": len(risk_rows),
                "risk_counts": {
                    "critical": tier_counts.get("critical", 0),
                    "high": tier_counts.get("high", 0),
                    "medium": tier_counts.get("medium", 0),
                    "low": tier_counts.get("low", 0),
                    "unknown": tier_counts.get("unknown", 0),
                },
            }

        except Exception as exc:
            logger.exception("Stockout risk run %s failed", run_id)
            self.db.rollback()
            risk_run = StockoutRiskRun(
                id=run_id,
                mode=mode,
                status="failed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                risk_horizon_days=horizon_days,
                error_message=str(exc),
            )
            self.db.add(risk_run)
            self.db.commit()
            raise

    # ------------------------------------------------------------------
    # Forecast run selection
    # ------------------------------------------------------------------

    def _select_forecast_run(
        self, forecast_run_id: Optional[str], mode: str
    ) -> Optional[ForecastRun]:
        if forecast_run_id:
            return (
                self.db.query(ForecastRun)
                .filter(ForecastRun.id == forecast_run_id, ForecastRun.status == "completed")
                .first()
            )

        if mode == "forward_planning":
            # 1. Prefer forward_planning completed
            run = (
                self.db.query(ForecastRun)
                .filter(
                    ForecastRun.status == "completed",
                    ForecastRun.mode == "forward_planning",
                )
                .order_by(ForecastRun.started_at.desc())
                .first()
            )
            if run:
                return run

        # 2. Fall back to any completed run (historical simulation)
        return (
            self.db.query(ForecastRun)
            .filter(ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )

    def _resolve_as_of_date(self, frun: ForecastRun, effective_mode: str) -> date:
        if effective_mode == "forward_planning":
            # as_of_date = latest inventory_daily date (i.e., "today" of our data)
            row = (
                self.db.query(func.max(InventoryDaily.date))
                .scalar()
            )
            if row:
                return row
            # Fallback: day before first forecast date
            first_fc = (
                self.db.query(func.min(Forecast.forecast_date))
                .filter(Forecast.forecast_run_id == frun.id)
                .scalar()
            )
            if first_fc:
                return first_fc - timedelta(days=1)
        # Historical simulation: as_of_date = backtest test_start_date
        return frun.test_start_date or frun.train_end_date or date.today()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_current_inventory(self, as_of_date: date) -> dict:
        """
        Returns {(product_id, store_id): {"on_hand": float, "available": float}}
        using the latest inventory_daily row on or before as_of_date.
        """
        # Subquery: max date per (product, store) up to as_of_date
        subq = (
            self.db.query(
                InventoryDaily.product_id,
                InventoryDaily.store_id,
                func.max(InventoryDaily.date).label("max_date"),
            )
            .filter(InventoryDaily.date <= as_of_date)
            .group_by(InventoryDaily.product_id, InventoryDaily.store_id)
            .subquery()
        )
        rows = (
            self.db.query(InventoryDaily)
            .join(
                subq,
                (InventoryDaily.product_id == subq.c.product_id)
                & (InventoryDaily.store_id == subq.c.store_id)
                & (InventoryDaily.date == subq.c.max_date),
            )
            .all()
        )
        inv = {}
        for r in rows:
            on_hand = r.on_hand_units or 0.0
            # inventory_daily does not track reserved separately; available = on_hand
            inv[(r.product_id, r.store_id)] = {
                "on_hand": on_hand,
                "available": on_hand,
                "inventory_date": r.date,
            }
        return inv

    def _load_inbound_pos(self, as_of_date: date, horizon_days: int) -> dict:
        """
        Returns {(product_id, store_id): total_inbound_units}
        for POs expected within [as_of_date+1, as_of_date+horizon_days]
        and with open/inbound status.
        """
        horizon_end = as_of_date + timedelta(days=horizon_days)
        rows = (
            self.db.query(RawPurchaseOrder)
            .filter(
                RawPurchaseOrder.expected_delivery_date > as_of_date,
                RawPurchaseOrder.expected_delivery_date <= horizon_end,
                RawPurchaseOrder.status.in_(list(_INBOUND_PO_STATUSES)),
            )
            .all()
        )
        inbound: dict = {}
        for po in rows:
            key = (po.product_id, po.store_id)
            inbound[key] = inbound.get(key, 0.0) + (po.quantity_ordered or 0.0)
        return inbound

    def _load_product_info(self) -> dict:
        """Returns {product_id: {supplier_id, unit_price, category}} from raw_products."""
        rows = self.db.query(RawProduct).all()
        return {
            r.id: {
                "supplier_id": r.supplier_id,
                "unit_price": r.unit_price or 0.0,
                "category": r.category or "unknown",
                "name": r.name or "",
            }
            for r in rows
        }

    def _load_supplier_info(self) -> dict:
        """Returns {supplier_id: {lead_time_days, reliability_score}}."""
        rows = self.db.query(RawSupplier).all()
        return {
            r.id: {
                "lead_time_days": r.lead_time_days_max or r.lead_time_days_min or 7,
                "reliability_score": r.reliability_score,
            }
            for r in rows
        }

    def _load_demand_std(self) -> dict:
        """
        Returns {(product_id, store_id): demand_std_daily}
        using rolling_units_std_7d from the last feature_matrix row per series.
        Fallback: rolling_units_std_28d. Final fallback: 0.0.
        """
        subq = (
            self.db.query(
                FeatureMatrix.product_id,
                FeatureMatrix.store_id,
                func.max(FeatureMatrix.date).label("max_date"),
            )
            .group_by(FeatureMatrix.product_id, FeatureMatrix.store_id)
            .subquery()
        )
        rows = (
            self.db.query(FeatureMatrix)
            .join(
                subq,
                (FeatureMatrix.product_id == subq.c.product_id)
                & (FeatureMatrix.store_id == subq.c.store_id)
                & (FeatureMatrix.date == subq.c.max_date),
            )
            .all()
        )
        std_map = {}
        for r in rows:
            std_val = r.rolling_units_std_7d
            if std_val is None:
                std_val = r.rolling_units_std_28d
            std_map[(r.product_id, r.store_id)] = _safe_float(std_val) or 0.0
        return std_map

    def _load_forecast_rows(
        self, frun: ForecastRun, as_of_date: date, horizon_days: int, effective_mode: str
    ) -> list:
        """Load forecast rows relevant for the risk horizon."""
        if effective_mode == "forward_planning":
            # Future dates: as_of_date+1 .. as_of_date+horizon_days
            horizon_start = as_of_date + timedelta(days=1)
            horizon_end = as_of_date + timedelta(days=horizon_days)
        else:
            # Historical simulation: test window of the backtest run
            horizon_start = frun.test_start_date
            horizon_end = frun.test_end_date or (
                frun.test_start_date + timedelta(days=horizon_days - 1)
                if frun.test_start_date else None
            )
            if horizon_start is None:
                return []

        query = (
            self.db.query(Forecast)
            .filter(Forecast.forecast_run_id == frun.id)
        )
        if horizon_start:
            query = query.filter(Forecast.forecast_date >= horizon_start)
        if horizon_end:
            query = query.filter(Forecast.forecast_date <= horizon_end)
        return query.all()

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _compute_risk_rows(
        self,
        forecast_rows: list,
        inventory_map: dict,
        inbound_map: dict,
        product_map: dict,
        supplier_map: dict,
        std_map: dict,
        risk_run_id: str,
        as_of_date: date,
        horizon_days: int,
        frun: ForecastRun,
    ) -> tuple[list[dict], dict]:
        # Group forecast rows by (product_id, store_id)
        series: dict = {}
        for fc in forecast_rows:
            key = (fc.product_id, fc.store_id)
            if key not in series:
                series[key] = []
            series[key].append(fc)

        risk_rows = []
        tier_counts: dict = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
        now = datetime.utcnow()

        for (product_id, store_id), fc_list in series.items():
            prod_info = product_map.get(product_id, {})
            supplier_id = prod_info.get("supplier_id")
            supplier_info = supplier_map.get(supplier_id, {}) if supplier_id else {}
            inv_info = inventory_map.get((product_id, store_id), {})
            inbound_units = inbound_map.get((product_id, store_id), 0.0)

            # Inventory
            on_hand = inv_info.get("on_hand", None)
            available = inv_info.get("available", None)

            # Supplier
            lead_time_days = supplier_info.get("lead_time_days", None)
            reliability_score = supplier_info.get("reliability_score", None)
            retail_price = prod_info.get("unit_price", 0.0)
            category = prod_info.get("category", "unknown")

            # Demand std (for safety stock)
            demand_std = std_map.get((product_id, store_id), 0.0)

            # Forecast demand aggregation
            p50_vals = [fc.p50_units for fc in fc_list if fc.p50_units is not None]
            p90_vals = [
                (fc.p90_units if fc.p90_units is not None else fc.p50_units)
                for fc in fc_list
                if (fc.p90_units is not None or fc.p50_units is not None)
            ]

            # Determine if we have enough data
            missing_forecast = len(p50_vals) == 0
            missing_inventory = available is None
            missing_supplier = lead_time_days is None

            if missing_forecast or missing_inventory:
                tier = "unknown"
                risk_reason = []
                if missing_forecast:
                    risk_reason.append("no forecast data")
                if missing_inventory:
                    risk_reason.append("no inventory data")
                if missing_supplier:
                    risk_reason.append("no supplier data")

                row = self._build_risk_row(
                    id=str(uuid.uuid4()),
                    risk_run_id=risk_run_id,
                    as_of_date=as_of_date,
                    product_id=product_id,
                    store_id=store_id,
                    category=category,
                    supplier_id=supplier_id,
                    forecast_run_id=frun.id,
                    model_type=frun.model_type,
                    model_name=frun.model_name,
                    forecast_horizon_days=horizon_days,
                    on_hand=on_hand,
                    available=available,
                    inbound=inbound_units,
                    lead_time_days=lead_time_days,
                    reliability_score=reliability_score,
                    forecast_p50=None,
                    forecast_p90=None,
                    avg_daily=None,
                    proj_p50=None,
                    proj_p90=None,
                    days_of_supply=None,
                    days_until_stockout=None,
                    expected_stockout_date=None,
                    safety_stock=None,
                    coverage_ratio=None,
                    lost_units=None,
                    lost_value=None,
                    risk_tier="unknown",
                    risk_score=None,
                    risk_reason="; ".join(risk_reason),
                    created_at=now,
                )
                risk_rows.append(row)
                tier_counts["unknown"] = tier_counts.get("unknown", 0) + 1
                continue

            # Aggregate demand
            forecast_p50 = sum(p50_vals)
            forecast_p90 = sum(p90_vals) if p90_vals else forecast_p50
            actual_horizon = len(p50_vals)
            avg_daily = forecast_p50 / actual_horizon if actual_horizon > 0 else 0.0

            # Projected end inventory
            avail = available or 0.0
            proj_p50 = avail + inbound_units - forecast_p50
            proj_p90 = avail + inbound_units - forecast_p90

            # Days of supply
            if avg_daily > 0:
                dos = avail / avg_daily
            else:
                dos = None  # no demand → no stockout risk

            # Days until stockout
            if proj_p50 >= 0 or avg_daily <= 0:
                days_until_stockout = None
                expected_stockout_date = None
            else:
                total_buffer = avail + inbound_units
                if avg_daily > 0:
                    days_until_stockout = total_buffer / avg_daily
                    days_until_stockout = max(0.0, min(float(days_until_stockout), float(horizon_days)))
                    expected_stockout_date = as_of_date + timedelta(days=days_until_stockout)
                else:
                    days_until_stockout = None
                    expected_stockout_date = None

            # Safety stock
            if lead_time_days and demand_std is not None and lead_time_days > 0:
                safety_stock = _Z_SCORE * demand_std * math.sqrt(lead_time_days)
            else:
                safety_stock = 0.0

            # Coverage ratio
            coverage_ratio = (avail + inbound_units) / max(forecast_p50, 1.0)

            # Lost sales
            lost_units = max(0.0, forecast_p50 - avail - inbound_units)
            lost_value = lost_units * (retail_price or 0.0)

            # Risk tier
            tier, reason = self._assign_risk_tier(
                days_until_stockout=days_until_stockout,
                lead_time_days=lead_time_days,
                proj_p50=proj_p50,
                proj_p90=proj_p90,
                coverage_ratio=coverage_ratio,
                safety_stock=safety_stock,
            )

            # Risk score
            risk_score = self._compute_risk_score(
                tier=tier,
                reliability_score=reliability_score,
                lost_value=lost_value,
            )

            row = self._build_risk_row(
                id=str(uuid.uuid4()),
                risk_run_id=risk_run_id,
                as_of_date=as_of_date,
                product_id=product_id,
                store_id=store_id,
                category=category,
                supplier_id=supplier_id,
                forecast_run_id=frun.id,
                model_type=frun.model_type,
                model_name=frun.model_name,
                forecast_horizon_days=horizon_days,
                on_hand=on_hand,
                available=avail,
                inbound=inbound_units,
                lead_time_days=lead_time_days,
                reliability_score=reliability_score,
                forecast_p50=forecast_p50,
                forecast_p90=forecast_p90,
                avg_daily=avg_daily,
                proj_p50=proj_p50,
                proj_p90=proj_p90,
                days_of_supply=dos,
                days_until_stockout=days_until_stockout,
                expected_stockout_date=expected_stockout_date,
                safety_stock=safety_stock,
                coverage_ratio=coverage_ratio,
                lost_units=lost_units,
                lost_value=lost_value,
                risk_tier=tier,
                risk_score=risk_score,
                risk_reason=reason,
                created_at=now,
            )
            risk_rows.append(row)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return risk_rows, tier_counts

    def _assign_risk_tier(
        self,
        days_until_stockout: Optional[float],
        lead_time_days: Optional[int],
        proj_p50: float,
        proj_p90: float,
        coverage_ratio: float,
        safety_stock: float,
    ) -> tuple[str, str]:
        """
        Deterministic risk tier assignment.

        critical : days_until_stockout is not null AND <= min(7, lead_time_days)
        high     : proj_p50 < 0 OR coverage_ratio < 1.0
        medium   : proj_p90 < safety_stock OR coverage_ratio < 1.25
        low      : proj_p90 >= safety_stock AND coverage_ratio >= 1.25
        """
        effective_lead = min(7, lead_time_days) if lead_time_days else 7

        if days_until_stockout is not None and days_until_stockout <= effective_lead:
            return "critical", (
                f"Stockout in {days_until_stockout:.1f}d <= lead time {effective_lead}d"
            )

        if proj_p50 < 0:
            return "high", (
                f"Projected p50 inventory negative ({proj_p50:.1f})"
            )

        if coverage_ratio < 1.0:
            return "high", (
                f"Coverage ratio {coverage_ratio:.2f} < 1.0 (demand exceeds supply)"
            )

        if proj_p90 < safety_stock:
            return "medium", (
                f"p90 projection ({proj_p90:.1f}) < safety stock ({safety_stock:.1f})"
            )

        if coverage_ratio < 1.25:
            return "medium", (
                f"Coverage ratio {coverage_ratio:.2f} < 1.25 (thin buffer)"
            )

        return "low", (
            f"Coverage ratio {coverage_ratio:.2f} >= 1.25 and p90 >= safety stock"
        )

    def _compute_risk_score(
        self,
        tier: str,
        reliability_score: Optional[float],
        lost_value: float,
    ) -> Optional[float]:
        """
        Numeric risk score 0–100.

        Base from tier + adjustments:
          - Low supplier reliability (< 0.8): +5 points
          - Lost sales value > 1000: +2 points (capped at 5)
        """
        base = _TIER_BASE_SCORE.get(tier)
        if base is None:
            return None
        adjustment = 0.0
        if reliability_score is not None and reliability_score < 0.8:
            adjustment += 5.0
        if lost_value > 1000:
            adjustment += min(5.0, lost_value / 10000)
        return min(100.0, base + adjustment)

    # ------------------------------------------------------------------
    # Row builder
    # ------------------------------------------------------------------

    def _build_risk_row(self, **kwargs) -> dict:
        """Build a dict suitable for bulk_insert_mappings(StockoutRisk, ...)."""
        return {
            "id": kwargs["id"],
            "risk_run_id": kwargs["risk_run_id"],
            "as_of_date": kwargs["as_of_date"],
            "product_id": kwargs["product_id"],
            "store_id": kwargs["store_id"],
            "category": kwargs.get("category"),
            "subcategory": None,
            "supplier_id": kwargs.get("supplier_id"),
            "forecast_run_id": kwargs.get("forecast_run_id"),
            "model_type": kwargs.get("model_type"),
            "model_name": kwargs.get("model_name"),
            "forecast_horizon_days": kwargs.get("forecast_horizon_days"),
            "current_on_hand_units": _safe_float(kwargs.get("on_hand")),
            "current_reserved_units": 0.0,
            "current_available_units": _safe_float(kwargs.get("available")),
            "inbound_units_within_horizon": _safe_float(kwargs.get("inbound", 0.0)),
            "supplier_lead_time_days": kwargs.get("lead_time_days"),
            "supplier_reliability_score": _safe_float(kwargs.get("reliability_score")),
            "forecast_demand_p50": _safe_float(kwargs.get("forecast_p50")),
            "forecast_demand_p90": _safe_float(kwargs.get("forecast_p90")),
            "average_daily_forecast": _safe_float(kwargs.get("avg_daily")),
            "projected_end_inventory_p50": _safe_float(kwargs.get("proj_p50")),
            "projected_end_inventory_p90": _safe_float(kwargs.get("proj_p90")),
            "days_of_supply": _safe_float(kwargs.get("days_of_supply")),
            "days_until_stockout": _safe_float(kwargs.get("days_until_stockout")),
            "expected_stockout_date": kwargs.get("expected_stockout_date"),
            "safety_stock_units": _safe_float(kwargs.get("safety_stock")),
            "inventory_coverage_ratio": _safe_float(kwargs.get("coverage_ratio")),
            "lost_sales_units_estimate": _safe_float(kwargs.get("lost_units")),
            "lost_sales_value_estimate": _safe_float(kwargs.get("lost_value")),
            "risk_score": _safe_float(kwargs.get("risk_score")),
            "risk_tier": kwargs.get("risk_tier", "unknown"),
            "risk_reason": kwargs.get("risk_reason"),
            "created_at": kwargs.get("created_at", datetime.utcnow()),
        }

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def _clear_previous_runs(
        self,
        mode: str,
        horizon_days: int,
        as_of_date: date,
        current_run_id: str,
    ) -> None:
        prev_runs = (
            self.db.query(StockoutRiskRun)
            .filter(
                StockoutRiskRun.mode == mode,
                StockoutRiskRun.risk_horizon_days == horizon_days,
                StockoutRiskRun.as_of_date == as_of_date,
                StockoutRiskRun.id != current_run_id,
                StockoutRiskRun.status == "completed",
            )
            .all()
        )
        for prev in prev_runs:
            self.db.query(StockoutRisk).filter(
                StockoutRisk.risk_run_id == prev.id
            ).delete(synchronize_session=False)
            self.db.delete(prev)
        if prev_runs:
            self.db.flush()

    # ------------------------------------------------------------------
    # Validation checks
    # ------------------------------------------------------------------

    def _build_checks(
        self, rows_created: int, tier_counts: dict, inventory_map: dict, inbound_map: dict
    ) -> list:
        return [
            {"name": "risk_rows_created", "status": "passed" if rows_created > 0 else "warning",
             "detail": f"{rows_created} risk rows"},
            {"name": "inventory_coverage", "status": "passed" if len(inventory_map) > 0 else "warning",
             "detail": f"{len(inventory_map)} product/store pairs with inventory"},
            {"name": "inbound_pos", "status": "passed",
             "detail": f"{len(inbound_map)} product/store pairs with inbound POs"},
            {"name": "unknown_tier", "status": "warning" if tier_counts.get("unknown", 0) > 0 else "passed",
             "detail": f"{tier_counts.get('unknown', 0)} rows with unknown tier (missing data)"},
        ]
