"""
Dashboard summary endpoints — Sprint 8.

These endpoints aggregate already-computed data for frontend display.
They do NOT introduce new business logic, forecasting formulas,
risk formulas, or recommendation formulas.

If no data exists, they return honest empty/readiness states.

GET /api/dashboard/overview
GET /api/dashboard/forecast-summary
GET /api/dashboard/risk-summary
GET /api/dashboard/recommendation-summary
GET /api/dashboard/model-summary
GET /api/dashboard/data-health
"""

import os

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    RawProduct, RawStore, RawOrder, RawInventorySnapshot,
    RawSupplier, RawPurchaseOrder,
    IngestionRun, AggregationRun, FeatureRun, FeatureMatrix,
    ForecastRun, Forecast, ModelMetric, ModelVersion,
    StockoutRiskRun, StockoutRisk,
    RecommendationRun, ReorderRecommendation,
    SalesDaily, InventoryDaily, ProductStoreDaily,
)
from app.schemas.api import (
    DashboardOverviewResponse,
    DashboardForecastSummaryResponse,
    DashboardRiskSummaryResponse,
    DashboardRecommendationSummaryResponse,
    DashboardModelSummaryResponse,
    DataHealthResponse,
    DashboardPipelineStatusResponse,
    DashboardProductResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /api/dashboard/overview
# ---------------------------------------------------------------------------

@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
def dashboard_overview(db: Session = Depends(get_db)):
    """
    Aggregated overview for the dashboard home/overview page.

    Returns raw counts, pipeline readiness state, and summary counts from
    the latest completed runs. All values are computed — no hardcoded metrics.
    """
    products_count = db.query(func.count(RawProduct.id)).scalar() or 0
    stores_count   = db.query(func.count(RawStore.id)).scalar() or 0
    orders_count   = db.query(func.count(RawOrder.id)).scalar() or 0
    inv_count      = db.query(func.count(RawInventorySnapshot.id)).scalar() or 0

    fm_count = db.query(func.count(FeatureMatrix.id)).scalar() or 0
    forecast_count = db.query(func.count(Forecast.id)).scalar() or 0

    latest_frun = (
        db.query(ForecastRun)
        .filter(ForecastRun.status == "completed")
        .order_by(ForecastRun.started_at.desc())
        .first()
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
    latest_feat = (
        db.query(FeatureRun)
        .filter(FeatureRun.status == "completed")
        .order_by(FeatureRun.started_at.desc())
        .first()
    )

    estimated_lost_sales = None
    if latest_risk_run:
        val = (
            db.query(func.sum(StockoutRisk.lost_sales_value_estimate))
            .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
            .scalar()
        )
        if val is not None:
            estimated_lost_sales = float(val)

    open_rec_count = 0
    estimated_order_cost = None
    if latest_rec_run:
        open_rec_count = (
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
        if cost_val is not None:
            estimated_order_cost = float(cost_val)

    return DashboardOverviewResponse(
        status="ok" if products_count > 0 else "no_data",
        raw_counts={
            "products": products_count,
            "stores": stores_count,
            "orders": orders_count,
            "inventory_snapshots": inv_count,
        },
        pipeline_readiness={
            "data_seeded": products_count > 0,
            "aggregation_run": (
                db.query(AggregationRun)
                .filter(AggregationRun.status == "success")
                .first()
            ) is not None,
            "features_built": fm_count > 0,
            "feature_rows": fm_count,
            "latest_feature_run_status": latest_feat.status if latest_feat else None,
            "forecast_run": latest_frun is not None,
            "latest_forecast_model": latest_frun.model_type if latest_frun else None,
            "risk_run": latest_risk_run is not None,
            "recommendation_run": latest_rec_run is not None,
        },
        risk_summary={
            "latest_run_id": latest_risk_run.id if latest_risk_run else None,
            "as_of_date": str(latest_risk_run.as_of_date) if latest_risk_run and latest_risk_run.as_of_date else None,
            "critical": latest_risk_run.critical_count if latest_risk_run else 0,
            "high": latest_risk_run.high_count if latest_risk_run else 0,
            "medium": latest_risk_run.medium_count if latest_risk_run else 0,
            "low": latest_risk_run.low_count if latest_risk_run else 0,
            "estimated_lost_sales_value": estimated_lost_sales,
        },
        recommendation_summary={
            "latest_run_id": latest_rec_run.id if latest_rec_run else None,
            "open_count": open_rec_count,
            "critical": latest_rec_run.critical_count if latest_rec_run else 0,
            "high": latest_rec_run.high_count if latest_rec_run else 0,
            "medium": latest_rec_run.medium_count if latest_rec_run else 0,
            "low": latest_rec_run.low_count if latest_rec_run else 0,
            "total_recommended_units": float(latest_rec_run.total_recommended_units or 0) if latest_rec_run else 0,
            "estimated_order_cost": estimated_order_cost,
        },
        forecast_summary={
            "latest_run_id": latest_frun.id if latest_frun else None,
            "model_type": latest_frun.model_type if latest_frun else None,
            "mode": latest_frun.mode if latest_frun else None,
            "horizon_days": latest_frun.horizon_days if latest_frun else None,
            "forecast_rows": forecast_count,
            "status": latest_frun.status if latest_frun else None,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/forecast-summary
# ---------------------------------------------------------------------------

@router.get("/dashboard/forecast-summary", response_model=DashboardForecastSummaryResponse)
def dashboard_forecast_summary(db: Session = Depends(get_db)):
    """Compact forecast summary for the forecasts dashboard page."""
    latest_frun = (
        db.query(ForecastRun)
        .filter(ForecastRun.status == "completed")
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    if not latest_frun:
        return DashboardForecastSummaryResponse(
            status="no_data",
            has_forecast=False,
            message="No completed forecast run. POST /api/forecasts/baseline/run first.",
        )

    overall_metric = (
        db.query(ModelMetric)
        .filter(ModelMetric.run_id == latest_frun.id, ModelMetric.level == "overall")
        .first()
    )

    return DashboardForecastSummaryResponse(
        status="ok",
        has_forecast=True,
        latest_run={
            "run_id": latest_frun.id,
            "model_type": latest_frun.model_type,
            "mode": latest_frun.mode,
            "horizon_days": latest_frun.horizon_days,
            "rows_created": latest_frun.rows_created or 0,
            "started_at": str(latest_frun.started_at) if latest_frun.started_at else None,
            "completed_at": str(latest_frun.completed_at) if latest_frun.completed_at else None,
        },
        metrics={
            "mae": overall_metric.mae if overall_metric else None,
            "rmse": overall_metric.rmse if overall_metric else None,
            "wape": overall_metric.wape if overall_metric else None,
            "smape": overall_metric.smape if overall_metric else None,
            "bias": overall_metric.bias if overall_metric else None,
            "rows_evaluated": overall_metric.rows_evaluated if overall_metric else 0,
        } if overall_metric else None,
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/risk-summary
# ---------------------------------------------------------------------------

@router.get("/dashboard/risk-summary", response_model=DashboardRiskSummaryResponse)
def dashboard_risk_summary(db: Session = Depends(get_db)):
    """Compact risk summary for the inventory risk dashboard page."""
    latest_run = (
        db.query(StockoutRiskRun)
        .filter(StockoutRiskRun.status == "completed")
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    if not latest_run:
        return DashboardRiskSummaryResponse(
            status="no_data",
            has_risk_run=False,
            tier_counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0},
            message="No completed risk run. POST /api/risks/run first.",
        )

    lost_sales_val = (
        db.query(func.sum(StockoutRisk.lost_sales_value_estimate))
        .filter(StockoutRisk.risk_run_id == latest_run.id)
        .scalar()
    )

    return DashboardRiskSummaryResponse(
        status="ok",
        has_risk_run=True,
        latest_run={
            "run_id": latest_run.id,
            "mode": latest_run.mode,
            "as_of_date": str(latest_run.as_of_date) if latest_run.as_of_date else None,
            "risk_horizon_days": latest_run.risk_horizon_days,
            "rows_created": latest_run.rows_created or 0,
            "started_at": str(latest_run.started_at) if latest_run.started_at else None,
        },
        tier_counts={
            "critical": latest_run.critical_count or 0,
            "high": latest_run.high_count or 0,
            "medium": latest_run.medium_count or 0,
            "low": latest_run.low_count or 0,
            "unknown": latest_run.unknown_count or 0,
        },
        estimated_lost_sales_value=float(lost_sales_val) if lost_sales_val else None,
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/recommendation-summary
# ---------------------------------------------------------------------------

@router.get("/dashboard/recommendation-summary", response_model=DashboardRecommendationSummaryResponse)
def dashboard_recommendation_summary(db: Session = Depends(get_db)):
    """Compact recommendation summary for the recommendations dashboard page."""
    latest_run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    if not latest_run:
        return DashboardRecommendationSummaryResponse(
            status="no_data",
            has_recommendation_run=False,
            urgency_counts={"critical": 0, "high": 0, "medium": 0, "low": 0},
            open_count=0,
            message="No completed recommendation run. POST /api/recommendations/run first.",
        )

    open_count = (
        db.query(func.count(ReorderRecommendation.id))
        .filter(
            ReorderRecommendation.recommendation_run_id == latest_run.id,
            ReorderRecommendation.status == "open",
        )
        .scalar() or 0
    )
    cost_val = (
        db.query(func.sum(ReorderRecommendation.estimated_order_cost))
        .filter(ReorderRecommendation.recommendation_run_id == latest_run.id)
        .scalar()
    )

    return DashboardRecommendationSummaryResponse(
        status="ok",
        has_recommendation_run=True,
        latest_run={
            "run_id": latest_run.id,
            "as_of_date": str(latest_run.as_of_date) if latest_run.as_of_date else None,
            "rows_created": latest_run.rows_created or 0,
            "started_at": str(latest_run.started_at) if latest_run.started_at else None,
        },
        urgency_counts={
            "critical": latest_run.critical_count or 0,
            "high": latest_run.high_count or 0,
            "medium": latest_run.medium_count or 0,
            "low": latest_run.low_count or 0,
        },
        open_count=open_count,
        total_estimated_order_cost=float(cost_val) if cost_val else None,
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/model-summary
# ---------------------------------------------------------------------------

@router.get("/dashboard/model-summary", response_model=DashboardModelSummaryResponse)
def dashboard_model_summary(db: Session = Depends(get_db)):
    """Compact ML model summary for the model-performance dashboard page."""
    latest_ml = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.status == "completed",
            ModelVersion.model_type == "ml_global_regressor",
        )
        .order_by(ModelVersion.created_at.desc())
        .first()
    )
    if not latest_ml:
        return DashboardModelSummaryResponse(
            status="no_data",
            has_ml_model=False,
            message="No completed ML model. POST /api/models/train first.",
        )

    # Get best baseline comparison
    best_baseline_wape = None
    best_baseline_type = None
    for bt in ["seasonal_naive", "moving_average_7d", "moving_average_28d"]:
        brun = (
            db.query(ForecastRun)
            .filter(ForecastRun.model_type == bt, ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )
        if brun:
            bmm = (
                db.query(ModelMetric)
                .filter(ModelMetric.run_id == brun.id, ModelMetric.level == "overall")
                .first()
            )
            if bmm and bmm.wape is not None:
                if best_baseline_wape is None or bmm.wape < best_baseline_wape:
                    best_baseline_wape = bmm.wape
                    best_baseline_type = bt

    ml_wape = (
        latest_ml.metrics_summary_json.get("overall", {}).get("wape")
        if latest_ml.metrics_summary_json else None
    )
    wape_delta = None
    ml_won = None
    if ml_wape is not None and best_baseline_wape is not None:
        wape_delta = round(ml_wape - best_baseline_wape, 6)
        ml_won = ml_wape < best_baseline_wape

    return DashboardModelSummaryResponse(
        status="ok",
        has_ml_model=True,
        latest_model_version={
            "model_version_id": latest_ml.id,
            "algorithm": latest_ml.algorithm,
            "model_type": latest_ml.model_type,
            "status": latest_ml.status,
            "trained_at": str(latest_ml.trained_at) if latest_ml.trained_at else None,
            "artifact_exists": (
                latest_ml.artifact_path is not None
                and os.path.exists(latest_ml.artifact_path)
            ),
            "ml_wape": ml_wape,
        },
        baseline_comparison={
            "best_baseline_model_type": best_baseline_type,
            "best_baseline_wape": best_baseline_wape,
            "ml_wape": ml_wape,
            "wape_delta": wape_delta,
            "ml_won": ml_won,
        } if best_baseline_wape is not None else None,
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/data-health
# ---------------------------------------------------------------------------

@router.get("/dashboard/data-health")
def dashboard_data_health(db: Session = Depends(get_db)):
    """
    Compact data-health snapshot for the data-health dashboard page.

    Delegates to the same logic as /api/data-health but returns a dashboard-
    oriented shape.  Importing the route function directly avoids duplication.
    """
    from app.api.overview import get_data_health as _get_data_health
    return _get_data_health(db=db)


# ---------------------------------------------------------------------------
# GET /api/dashboard/pipeline-status
# ---------------------------------------------------------------------------

@router.get("/dashboard/pipeline-status", response_model=DashboardPipelineStatusResponse)
def dashboard_pipeline_status(db: Session = Depends(get_db)):
    """
    One-shot pipeline readiness status for the Pipeline page.

    Returns the status and last-run info for every pipeline stage in the
    expected execution order. No new business logic — reads existing run tables.
    """
    products_count = db.query(func.count(RawProduct.id)).scalar() or 0

    latest_ingestion = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .first()
    )
    latest_aggregation = (
        db.query(AggregationRun)
        .order_by(AggregationRun.started_at.desc())
        .first()
    )
    latest_feature = (
        db.query(FeatureRun)
        .order_by(FeatureRun.started_at.desc())
        .first()
    )
    latest_baseline = (
        db.query(ForecastRun)
        .filter(ForecastRun.backtest_mode == True)
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    latest_ml = (
        db.query(ModelVersion)
        .filter(ModelVersion.model_type == "ml_global_regressor")
        .order_by(ModelVersion.created_at.desc())
        .first()
    )
    latest_planning = (
        db.query(ForecastRun)
        .filter(ForecastRun.backtest_mode == False)
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    latest_risk = (
        db.query(StockoutRiskRun)
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    latest_rec = (
        db.query(RecommendationRun)
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )

    def _run_status(run, status_field: str = "status") -> str:
        if run is None:
            return "not_run"
        return getattr(run, status_field, "unknown") or "unknown"

    def _run_info(run) -> dict | None:
        if run is None:
            return None
        info: dict = {"id": run.id}
        for attr in ("status", "started_at", "completed_at", "finished_at",
                     "rows_created", "records_produced", "model_type",
                     "mode", "as_of_date", "risk_horizon_days"):
            val = getattr(run, attr, None)
            info[attr] = str(val) if val is not None else None
        return info

    steps = [
        {
            "step": "reset_demo",
            "label": "Reset / Seed Demo Data",
            "endpoint": "POST /api/demo/reset",
            "status": "completed" if products_count > 0 else "not_run",
            "detail": f"{products_count} products seeded" if products_count > 0 else None,
        },
        {
            "step": "aggregation",
            "label": "Run Aggregation",
            "endpoint": "POST /api/aggregation/run",
            "status": _run_status(latest_aggregation, "status").replace("success", "completed"),
            "last_run": _run_info(latest_aggregation),
        },
        {
            "step": "features",
            "label": "Build Features",
            "endpoint": "POST /api/features/build",
            "status": _run_status(latest_feature),
            "last_run": _run_info(latest_feature),
        },
        {
            "step": "baseline_forecast",
            "label": "Run Baseline Forecast",
            "endpoint": "POST /api/forecasts/baseline/run",
            "status": _run_status(latest_baseline),
            "last_run": _run_info(latest_baseline),
        },
        {
            "step": "train_ml",
            "label": "Train ML Model",
            "endpoint": "POST /api/models/train",
            "status": _run_status(latest_ml),
            "last_run": _run_info(latest_ml),
        },
        {
            "step": "planning_forecast",
            "label": "Run Planning Forecast",
            "endpoint": "POST /api/forecasts/planning/run",
            "status": _run_status(latest_planning),
            "last_run": _run_info(latest_planning),
        },
        {
            "step": "stockout_risk",
            "label": "Run Stockout Risk",
            "endpoint": "POST /api/risks/run",
            "status": _run_status(latest_risk),
            "last_run": _run_info(latest_risk),
        },
        {
            "step": "recommendations",
            "label": "Run Recommendations",
            "endpoint": "POST /api/recommendations/run",
            "status": _run_status(latest_rec),
            "last_run": _run_info(latest_rec),
        },
    ]

    all_done = all(s["status"] in ("completed", "success") for s in steps)

    return DashboardPipelineStatusResponse(
        status="ok",
        all_steps_complete=all_done,
        steps=steps,
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/product/{product_id}
# ---------------------------------------------------------------------------

@router.get("/dashboard/product/{product_id}", response_model=DashboardProductResponse)
def dashboard_product(product_id: str, db: Session = Depends(get_db)):
    """
    Read-only product drilldown for the dashboard.

    Returns product metadata, latest risk per store, and latest
    recommendations per store — all from already-computed persisted data.
    No new business logic.
    """
    product = db.query(RawProduct).filter(RawProduct.id == product_id).first()
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found.")

    # Latest risk run
    latest_risk_run = (
        db.query(StockoutRiskRun)
        .filter(StockoutRiskRun.status == "completed")
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    risk_rows: list[dict] = []
    if latest_risk_run:
        risks = (
            db.query(StockoutRisk)
            .filter(
                StockoutRisk.risk_run_id == latest_risk_run.id,
                StockoutRisk.product_id == product_id,
            )
            .all()
        )
        for r in risks:
            risk_rows.append({
                "store_id": r.store_id,
                "risk_tier": r.risk_tier,
                "risk_score": r.risk_score,
                "days_until_stockout": r.days_until_stockout,
                "current_available_units": r.current_available_units,
                "lost_sales_value_estimate": r.lost_sales_value_estimate,
                "risk_reason": r.risk_reason,
                "as_of_date": str(r.as_of_date) if r.as_of_date else None,
            })

    # Latest recommendation run
    latest_rec_run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    rec_rows: list[dict] = []
    if latest_rec_run:
        recs = (
            db.query(ReorderRecommendation)
            .filter(
                ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                ReorderRecommendation.product_id == product_id,
            )
            .all()
        )
        for r in recs:
            rec_rows.append({
                "store_id": r.store_id,
                "urgency": r.urgency,
                "recommended_units_rounded": r.recommended_units_rounded,
                "estimated_order_cost": r.estimated_order_cost,
                "estimated_lost_sales_avoided": r.estimated_lost_sales_avoided,
                "status": r.status,
                "days_until_stockout": r.days_until_stockout,
                "recommendation_reason": r.recommendation_reason,
            })

    # Latest forecast rows for this product
    latest_frun = (
        db.query(ForecastRun)
        .filter(ForecastRun.status == "completed")
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    forecast_rows: list[dict] = []
    if latest_frun:
        frows = (
            db.query(Forecast)
            .filter(
                Forecast.forecast_run_id == latest_frun.id,
                Forecast.product_id == product_id,
            )
            .order_by(Forecast.forecast_date)
            .limit(100)
            .all()
        )
        for f in frows:
            forecast_rows.append({
                "forecast_date": str(f.forecast_date) if f.forecast_date else None,
                "store_id": f.store_id,
                "p50_units": f.p50_units,
                "p10_units": f.p10_units,
                "p90_units": f.p90_units,
                "actual_units": f.actual_units,
            })

    supplier = None
    if product.supplier_id:
        sup = db.query(RawSupplier).filter(RawSupplier.id == product.supplier_id).first()
        if sup:
            supplier = {
                "supplier_id": sup.id,
                "name": sup.name,
                "lead_time_days_min": sup.lead_time_days_min,
                "lead_time_days_max": sup.lead_time_days_max,
                "reliability_score": sup.reliability_score,
            }

    return DashboardProductResponse(
        status="ok",
        product_id=product_id,
        product={
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "brand": product.brand,
            "unit_cost": product.unit_cost,
            "unit_price": product.unit_price,
            "lead_time_days": product.lead_time_days,
            "is_active": product.is_active,
            "supplier_id": product.supplier_id,
        },
        supplier=supplier,
        risk_rows=risk_rows,
        recommendation_rows=rec_rows,
        forecast_rows=forecast_rows,
    )
