"""
DataScienceSummaryService — Sprint 15.

Produces ML/data-science interpretation summaries from existing pipeline tables.
All reads are read-only; no DB mutations are performed.

Feature signal groups are derived from the same NUMERIC_FEATURES /
CATEGORICAL_FEATURES lists used by TrainingService, so they stay in sync
without duplicating the column definitions here.
"""

from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    RawProduct, RawStore, RawOrder, RawInventorySnapshot,
    FeatureMatrix, ForecastRun, Forecast, ModelMetric, ModelVersion,
    StockoutRisk, StockoutRiskRun, ReorderRecommendation, RecommendationRun,
)
from app.services.training_service import ALL_FEATURE_COLUMNS, NUMERIC_FEATURES, CATEGORICAL_FEATURES
from app.schemas.data_science import (
    DataScienceSummaryResponse, DataVolumeSchema, ModelStatusSchema, DecisionStatusSchema,
    ForecastDiagnosticsResponse, ModelDiagnosticSchema,
    ModelComparisonResponse, ModelComparisonEntrySchema,
    FeatureSignalsResponse, FeatureSignalGroupSchema,
    BusinessImpactResponse, TopRiskEntrySchema, TopRecommendationEntrySchema,
)

# ---------------------------------------------------------------------------
# WAPE interpretation thresholds
# ---------------------------------------------------------------------------

WAPE_GUIDE: dict[str, str] = {
    "strong": "WAPE below 30%: strong demand signal for planning purposes.",
    "directional": "WAPE 30–60%: usable directional signal. Treat forecasts as a planning guide.",
    "weak": "WAPE above 60%: weak / demonstration signal. Use cautiously; do not rely on point estimates.",
}


def _wape_label(wape: Optional[float]) -> str:
    if wape is None:
        return "unknown"
    if wape < 0.30:
        return "strong"
    if wape < 0.60:
        return "directional"
    return "weak"


def _wape_interpretation(wape: Optional[float], model_name: str) -> str:
    label = _wape_label(wape)
    if label == "unknown":
        return f"{model_name}: no WAPE metric available."
    if label == "strong":
        return (
            f"{model_name} WAPE {wape:.1%} — strong demo signal. "
            "Demand direction is reliable for inventory planning in this synthetic dataset."
        )
    if label == "directional":
        return (
            f"{model_name} WAPE {wape:.1%} — usable directional signal. "
            "Forecasts indicate demand direction but point estimates have meaningful uncertainty."
        )
    return (
        f"{model_name} WAPE {wape:.1%} — weak / demonstration signal. "
        "This is a prototype forecaster on a small synthetic dataset; "
        "do not treat point estimates as precise predictions."
    )


def _wape_warning(wape: Optional[float]) -> Optional[str]:
    if wape is None or wape < 0.60:
        return None
    return (
        f"WAPE {wape:.1%} exceeds the 60% weak-signal threshold. "
        "Forecasts are for directional planning only. "
        "This model is not production-calibrated."
    )


# ---------------------------------------------------------------------------
# Feature signal group definitions
# ---------------------------------------------------------------------------

_SIGNAL_GROUPS = [
    {
        "group": "Recent demand",
        "features": ["lag_units_1d", "lag_units_7d", "lag_units_14d", "lag_units_28d",
                     "rolling_units_mean_7d", "rolling_units_mean_14d", "rolling_units_mean_28d"],
        "interpretation": (
            "Recent sales history is one of the strongest demand signals. "
            "Lag and rolling-window features capture momentum and recency effects."
        ),
    },
    {
        "group": "Demand variability",
        "features": ["rolling_units_std_7d", "rolling_units_std_28d"],
        "interpretation": (
            "Demand variability features capture how stable or volatile demand is. "
            "Higher variability is associated with wider prediction intervals."
        ),
    },
    {
        "group": "Seasonality / calendar",
        "features": ["day_of_week", "week_of_year", "month", "quarter", "is_weekend"],
        "interpretation": (
            "Calendar features let the model learn weekly and seasonal demand patterns. "
            "Weekend effects and monthly cycles are common retail demand drivers."
        ),
    },
    {
        "group": "Price / margin",
        "features": ["retail_price", "unit_cost", "gross_margin_pct",
                     "rolling_revenue_mean_7d", "rolling_revenue_mean_28d",
                     "price_change_pct_7d", "price_change_pct_28d"],
        "interpretation": (
            "Price and margin features capture demand elasticity. "
            "Price changes are associated with short-term demand shifts."
        ),
    },
    {
        "group": "Promotion exposure",
        "features": ["promo_active", "discount_pct"],
        "interpretation": (
            "Promotion flags indicate when a product is on discount or active promotion. "
            "Promotions are associated with temporary demand lift."
        ),
    },
    {
        "group": "Inventory coverage",
        "features": ["available_units", "stockout_flag", "days_of_supply"],
        "interpretation": (
            "Inventory coverage features capture current stock levels. "
            "Stockout flags help the model learn when realized demand may be supply-constrained."
        ),
    },
    {
        "group": "Product age / lifecycle",
        "features": ["days_since_launch", "product_age_bucket"],
        "interpretation": (
            "Product lifecycle features distinguish new launches from established products. "
            "Demand patterns differ significantly across lifecycle stages."
        ),
    },
    {
        "group": "Store / channel",
        "features": ["category", "store_channel"],
        "interpretation": (
            "Category and channel features allow the global model to learn "
            "cross-product and cross-channel demand patterns simultaneously."
        ),
    },
]


def _build_feature_signals(feature_columns: list[str]) -> list[FeatureSignalGroupSchema]:
    feature_set = set(feature_columns)
    result = []
    for grp in _SIGNAL_GROUPS:
        matched = [f for f in grp["features"] if f in feature_set]
        result.append(FeatureSignalGroupSchema(
            group=grp["group"],
            available=len(matched) > 0,
            example_features=matched[:4],
            interpretation=grp["interpretation"],
        ))
    return result


# ---------------------------------------------------------------------------
# Model profile helpers
# ---------------------------------------------------------------------------

_MODEL_PROFILES: dict[str, dict] = {
    "seasonal_naive": {
        "label": "Seasonal Naive",
        "strengths": ["No training required", "Captures weekly seasonality", "Strong baseline"],
        "limitations": ["Cannot learn promotions or price changes", "No trend detection"],
        "best_for": "Stable, seasonal products with predictable weekly cycles",
    },
    "moving_average_7d": {
        "label": "7-Day Moving Average",
        "strengths": ["Simple and interpretable", "Adapts to recent demand levels"],
        "limitations": ["No seasonal correction", "Lags during demand shifts"],
        "best_for": "Short-horizon smoothing when recent sales are the best signal",
    },
    "moving_average_28d": {
        "label": "28-Day Moving Average",
        "strengths": ["Smooths short-term noise", "Stable medium-term estimate"],
        "limitations": ["Very slow to adapt", "No event or promotion awareness"],
        "best_for": "Slow-moving products with low volatility",
    },
    "hist_gradient_boosting": {
        "label": "HistGradientBoosting (ML)",
        "strengths": [
            "Learns from 30+ features simultaneously",
            "Handles promotions, price, and calendar effects",
            "Transfers learning from high- to low-volume SKUs",
        ],
        "limitations": [
            "Requires sufficient training data",
            "Black-box — individual forecasts are not easily interpretable",
            "Not production-calibrated on this synthetic demo dataset",
        ],
        "best_for": "Overall planning forecasts across a mixed product catalog",
    },
}


def _model_label(model_type: str) -> str:
    return _MODEL_PROFILES.get(model_type, {}).get("label", model_type)


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class DataScienceSummaryService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # /api/data-science/summary
    # ------------------------------------------------------------------

    def get_summary(self) -> DataScienceSummaryResponse:
        db = self.db

        products = db.query(func.count(RawProduct.id)).scalar() or 0
        stores = db.query(func.count(RawStore.id)).scalar() or 0
        orders = db.query(func.count(RawOrder.id)).scalar() or 0
        inv = db.query(func.count(RawInventorySnapshot.id)).scalar() or 0
        feature_rows = db.query(func.count(FeatureMatrix.id)).scalar() or 0
        forecast_rows = db.query(func.count(Forecast.id)).scalar() or 0

        # Build pipeline story based on what's actually present
        story = []
        if products > 0:
            story.append(f"Synthetic raw commerce data was seeded ({products} products, {stores} stores, {orders} orders).")
        if feature_rows > 0:
            story.append("Daily demand and inventory tables were aggregated from raw records.")
            story.append(f"Leakage-safe features were built across {feature_rows:,} (product, store, date) rows.")
        if forecast_rows > 0:
            story.append(f"Forecasting models were trained and evaluated ({forecast_rows:,} forecast rows generated).")

        latest_risk_run = (
            db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )
        if latest_risk_run:
            story.append("Stockout risk was scored for each (product, store) combination.")

        latest_rec_run = (
            db.query(RecommendationRun)
            .filter(RecommendationRun.status == "completed")
            .order_by(RecommendationRun.started_at.desc())
            .first()
        )
        if latest_rec_run:
            story.append("Internal reorder recommendations were computed for review.")

        if not story:
            story = ["No pipeline data found. Seed demo data and run the pipeline first."]

        # Latest model
        latest_ml = (
            db.query(ModelVersion)
            .filter(ModelVersion.status == "completed", ModelVersion.model_type == "ml_global_regressor")
            .order_by(ModelVersion.created_at.desc())
            .first()
        )
        latest_frun = (
            db.query(ForecastRun)
            .filter(ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )

        ml_wape = None
        latest_model_name = None
        if latest_ml and latest_ml.metrics_summary_json:
            ml_wape = latest_ml.metrics_summary_json.get("overall", {}).get("wape")
            latest_model_name = "hist_gradient_boosting"
        elif latest_frun:
            latest_model_name = latest_frun.model_type
            mm = (
                db.query(ModelMetric)
                .filter(ModelMetric.run_id == latest_frun.id, ModelMetric.level == "overall")
                .first()
            )
            if mm:
                ml_wape = mm.wape

        model_status = ModelStatusSchema(
            latest_model=latest_model_name,
            latest_wape=ml_wape,
            interpretation=_wape_interpretation(ml_wape, _model_label(latest_model_name or "")),
        )

        # Decision status
        critical_risks = 0
        high_risks = 0
        estimated_lost_sales = None
        if latest_risk_run:
            critical_risks = latest_risk_run.critical_count or 0
            high_risks = latest_risk_run.high_count or 0
            lsv = (
                db.query(func.sum(StockoutRisk.lost_sales_value_estimate))
                .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
                .scalar()
            )
            estimated_lost_sales = float(lsv) if lsv else None

        open_recs = 0
        estimated_order_cost = None
        if latest_rec_run:
            open_recs = (
                db.query(func.count(ReorderRecommendation.id))
                .filter(
                    ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                    ReorderRecommendation.status == "open",
                )
                .scalar() or 0
            )
            cost_val = (
                db.query(func.sum(ReorderRecommendation.estimated_order_cost))
                .filter(ReorderRecommendation.recommendation_run_id == latest_rec_run.id)
                .scalar()
            )
            estimated_order_cost = float(cost_val) if cost_val else None

        return DataScienceSummaryResponse(
            status="ok" if products > 0 else "no_data",
            pipeline_story=story,
            data_volume=DataVolumeSchema(
                products=products,
                stores=stores,
                orders=orders,
                inventory_snapshots=inv,
                feature_rows=feature_rows,
                forecast_rows=forecast_rows,
            ),
            model_status=model_status,
            decision_status=DecisionStatusSchema(
                critical_risks=critical_risks,
                high_risks=high_risks,
                open_recommendations=open_recs,
                estimated_lost_sales=estimated_lost_sales,
                estimated_order_cost=estimated_order_cost,
            ),
        )

    # ------------------------------------------------------------------
    # /api/data-science/forecast-diagnostics
    # ------------------------------------------------------------------

    def get_forecast_diagnostics(self) -> ForecastDiagnosticsResponse:
        db = self.db

        no_data_response = ForecastDiagnosticsResponse(
            status="no_data",
            has_model=False,
            message="No completed forecast run. Run the pipeline first.",
            baseline=None,
            ml_model=None,
            wape_interpretation_guide=WAPE_GUIDE,
        )

        def _build_diagnostic(run: ForecastRun) -> ModelDiagnosticSchema:
            mm = (
                db.query(ModelMetric)
                .filter(ModelMetric.run_id == run.id, ModelMetric.level == "overall")
                .first()
            )
            wape = mm.wape if mm else None
            mae = mm.mae if mm else None
            rmse = mm.rmse if mm else None
            bias = mm.bias if mm else None
            rows_evaluated = mm.rows_evaluated if mm else 0
            rows_created = run.rows_created or 0
            label = _wape_label(wape)
            return ModelDiagnosticSchema(
                model_name=_model_label(run.model_type),
                model_type=run.model_type,
                mae=round(mae, 4) if mae is not None else None,
                rmse=round(rmse, 4) if rmse is not None else None,
                wape=round(wape, 6) if wape is not None else None,
                bias=round(bias, 4) if bias is not None else None,
                forecast_rows=rows_created,
                backtest_horizon_days=run.horizon_days,
                interpretation=_wape_interpretation(wape, _model_label(run.model_type)),
                quality_label=label,
                warning=_wape_warning(wape),
            )

        # Latest ML run
        ml_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.model_type == "hist_gradient_boosting", ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )

        # Best baseline
        baseline_types = ["seasonal_naive", "moving_average_7d", "moving_average_28d"]
        best_baseline_run = None
        best_baseline_wape = None
        for bt in baseline_types:
            br = (
                db.query(ForecastRun)
                .filter(ForecastRun.model_type == bt, ForecastRun.status == "completed")
                .order_by(ForecastRun.started_at.desc())
                .first()
            )
            if br is None:
                continue
            bmm = (
                db.query(ModelMetric)
                .filter(ModelMetric.run_id == br.id, ModelMetric.level == "overall")
                .first()
            )
            if bmm and bmm.wape is not None:
                if best_baseline_wape is None or bmm.wape < best_baseline_wape:
                    best_baseline_wape = bmm.wape
                    best_baseline_run = br

        if ml_run is None and best_baseline_run is None:
            return no_data_response

        baseline_diag = _build_diagnostic(best_baseline_run) if best_baseline_run else None
        ml_diag = _build_diagnostic(ml_run) if ml_run else None

        return ForecastDiagnosticsResponse(
            status="ok",
            has_model=True,
            message=None,
            baseline=baseline_diag,
            ml_model=ml_diag,
            wape_interpretation_guide=WAPE_GUIDE,
        )

    # ------------------------------------------------------------------
    # /api/data-science/model-comparison
    # ------------------------------------------------------------------

    def get_model_comparison(self) -> ModelComparisonResponse:
        db = self.db
        entries: list[ModelComparisonEntrySchema] = []

        baseline_types = ["seasonal_naive", "moving_average_7d", "moving_average_28d"]
        all_types = baseline_types + ["hist_gradient_boosting"]

        for mt in all_types:
            run = (
                db.query(ForecastRun)
                .filter(ForecastRun.model_type == mt, ForecastRun.status == "completed")
                .order_by(ForecastRun.started_at.desc())
                .first()
            )
            if run is None:
                continue
            mm = (
                db.query(ModelMetric)
                .filter(ModelMetric.run_id == run.id, ModelMetric.level == "overall")
                .first()
            )
            profile = _MODEL_PROFILES.get(mt, {})
            wape = mm.wape if mm else None
            entries.append(ModelComparisonEntrySchema(
                model_name=_model_label(mt),
                model_type=mt,
                wape=round(wape, 6) if wape is not None else None,
                mae=round(mm.mae, 4) if mm and mm.mae is not None else None,
                rmse=round(mm.rmse, 4) if mm and mm.rmse is not None else None,
                bias=round(mm.bias, 4) if mm and mm.bias is not None else None,
                rank=0,
                quality_label=_wape_label(wape),
                strengths=profile.get("strengths", []),
                limitations=profile.get("limitations", []),
                best_for=profile.get("best_for", "General demand planning"),
            ))

        if not entries:
            return ModelComparisonResponse(
                status="no_data",
                has_comparison=False,
                message="No completed forecast runs to compare. Run baseline and/or ML forecasts first.",
                models=[],
            )

        # Rank by WAPE ascending (None WAPE goes last)
        entries.sort(key=lambda e: (e.wape is None, e.wape or 999))
        for i, entry in enumerate(entries):
            entry.rank = i + 1

        return ModelComparisonResponse(
            status="ok",
            has_comparison=len(entries) >= 2,
            message=None if len(entries) >= 2 else "Only one model run available — add more models for comparison.",
            models=entries,
        )

    # ------------------------------------------------------------------
    # /api/data-science/feature-signals
    # ------------------------------------------------------------------

    def get_feature_signals(self) -> FeatureSignalsResponse:
        db = self.db

        # Use the feature columns from the latest trained model if available;
        # otherwise fall back to the canonical feature list from TrainingService.
        latest_ml = (
            db.query(ModelVersion)
            .filter(ModelVersion.status == "completed", ModelVersion.model_type == "ml_global_regressor")
            .order_by(ModelVersion.created_at.desc())
            .first()
        )

        if latest_ml and latest_ml.feature_columns_json:
            feature_columns = latest_ml.feature_columns_json
            source = "trained_model"
        else:
            feature_columns = ALL_FEATURE_COLUMNS
            source = "feature_definition"

        signals = _build_feature_signals(feature_columns)

        return FeatureSignalsResponse(
            status="ok",
            source=source,
            total_features=len(feature_columns),
            signals=signals,
            disclaimer=(
                "Feature signal groups describe which types of information are used "
                "as inputs to the demand forecasting model. They indicate association, "
                "not causation. This is a prototype system on synthetic data."
            ),
        )

    # ------------------------------------------------------------------
    # /api/data-science/business-impact
    # ------------------------------------------------------------------

    def get_business_impact(self) -> BusinessImpactResponse:
        db = self.db

        no_data = BusinessImpactResponse(
            status="no_data",
            has_data=False,
            message="No completed risk or recommendation run. Run the full pipeline first.",
            estimated_lost_sales=None,
            estimated_order_cost=None,
            risk_tier_distribution={},
            recommendation_urgency_distribution={},
            top_risks=[],
            top_recommendations=[],
            review_guidance=["Run the demo pipeline to generate risk and recommendation data."],
            automation_note="No purchasing is automated. All recommendations are internal review guidance only.",
        )

        latest_risk_run = (
            db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )
        latest_rec_run = (
            db.query(RecommendationRun)
            .filter(RecommendationRun.status == "completed")
            .order_by(RecommendationRun.started_at.desc())
            .first()
        )

        if not latest_risk_run and not latest_rec_run:
            return no_data

        # Risk data
        estimated_lost_sales = None
        risk_tier_dist: dict[str, int] = {}
        top_risks: list[TopRiskEntrySchema] = []

        if latest_risk_run:
            lsv = (
                db.query(func.sum(StockoutRisk.lost_sales_value_estimate))
                .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
                .scalar()
            )
            estimated_lost_sales = float(lsv) if lsv else None

            for tier in ("critical", "high", "medium", "low", "unknown"):
                cnt = getattr(latest_risk_run, f"{tier}_count", 0) or 0
                if cnt > 0:
                    risk_tier_dist[tier] = cnt

            top_risk_rows = (
                db.query(StockoutRisk, RawProduct.name)
                .join(RawProduct, StockoutRisk.product_id == RawProduct.id, isouter=True)
                .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
                .order_by(
                    StockoutRisk.risk_score.desc().nullslast()
                )
                .limit(5)
                .all()
            )
            for row in top_risk_rows:
                risk, product_name = row
                top_risks.append(TopRiskEntrySchema(
                    product_id=risk.product_id,
                    product_name=product_name,
                    store_id=risk.store_id,
                    risk_tier=risk.risk_tier or "unknown",
                    days_until_stockout=risk.days_until_stockout,
                    lost_sales_value_estimate=risk.lost_sales_value_estimate,
                ))

        # Recommendation data
        estimated_order_cost = None
        rec_urgency_dist: dict[str, int] = {}
        top_recs: list[TopRecommendationEntrySchema] = []

        if latest_rec_run:
            cost_val = (
                db.query(func.sum(ReorderRecommendation.estimated_order_cost))
                .filter(ReorderRecommendation.recommendation_run_id == latest_rec_run.id)
                .scalar()
            )
            estimated_order_cost = float(cost_val) if cost_val else None

            for urg in ("critical", "high", "medium", "low"):
                cnt = getattr(latest_rec_run, f"{urg}_count", 0) or 0
                if cnt > 0:
                    rec_urgency_dist[urg] = cnt

            top_rec_rows = (
                db.query(ReorderRecommendation, RawProduct.name)
                .join(RawProduct, ReorderRecommendation.product_id == RawProduct.id, isouter=True)
                .filter(ReorderRecommendation.recommendation_run_id == latest_rec_run.id)
                .order_by(
                    ReorderRecommendation.estimated_lost_sales_avoided.desc().nullslast()
                )
                .limit(5)
                .all()
            )
            for row in top_rec_rows:
                rec, product_name = row
                top_recs.append(TopRecommendationEntrySchema(
                    product_id=rec.product_id,
                    product_name=product_name,
                    store_id=rec.store_id,
                    urgency=rec.urgency or "low",
                    recommended_units=rec.recommended_units_rounded,
                    estimated_order_cost=rec.estimated_order_cost,
                ))

        # Guidance
        guidance: list[str] = []
        critical = risk_tier_dist.get("critical", 0)
        high = risk_tier_dist.get("high", 0)
        if critical > 0:
            guidance.append(f"Review {critical} critical-risk product/store combination{'s' if critical > 1 else ''} first.")
        if high > 0:
            guidance.append(f"Then address {high} high-risk item{'s' if high > 1 else ''}.")
        if estimated_lost_sales:
            guidance.append(f"Total estimated lost sales exposure: €{estimated_lost_sales:,.0f}.")
        open_recs = (
            db.query(func.count(ReorderRecommendation.id))
            .filter(
                ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                ReorderRecommendation.status == "open",
            )
            .scalar() or 0
        ) if latest_rec_run else 0
        if open_recs:
            guidance.append(f"There are {open_recs} open reorder recommendations awaiting internal review.")
        if not guidance:
            guidance.append("No critical or high risks detected in the latest run.")

        return BusinessImpactResponse(
            status="ok",
            has_data=True,
            message=None,
            estimated_lost_sales=estimated_lost_sales,
            estimated_order_cost=estimated_order_cost,
            risk_tier_distribution=risk_tier_dist,
            recommendation_urgency_distribution=rec_urgency_dist,
            top_risks=top_risks,
            top_recommendations=top_recs,
            review_guidance=guidance,
            automation_note=(
                "No purchase order is created automatically. "
                "All recommendations are internal review guidance only. "
                "Reorder actions require explicit human approval."
            ),
        )
