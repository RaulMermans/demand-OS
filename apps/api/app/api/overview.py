from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import (
    RawProduct, RawStore, RawOrder, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
    IngestionRun, AggregationRun, SalesDaily, InventoryDaily, ProductStoreDaily,
    FeatureMatrix, FeatureRun, ForecastRun, Forecast, ModelMetric, ModelVersion,
    StockoutRiskRun, StockoutRisk, RecommendationRun, ReorderRecommendation,
)
from app.schemas.api import OverviewResponse, DataHealthResponse
from app.services.validation_service import ValidationService
from app.schemas.raw import (
    RawProduct as PydProduct, RawStore as PydStore,
    RawOrderLine as PydOrder, RawInventorySnapshot as PydInv,
    RawPromotion as PydPromo, RawSupplier as PydSup,
    RawPurchaseOrder as PydPO,
)

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    """Operational overview: pipeline status and record counts."""
    products_count = db.query(func.count(RawProduct.id)).scalar() or 0
    stores_count   = db.query(func.count(RawStore.id)).scalar() or 0
    orders_count   = db.query(func.count(RawOrder.id)).scalar() or 0

    latest_run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .first()
    )

    if products_count == 0:
        return OverviewResponse(
            status="no_data",
            data_mode="mock",
            pipeline_ready=False,
            message="No data ingested yet. Run POST /api/demo/reset to seed the demo dataset.",
            summary={
                "products": 0,
                "stores": 0,
                "orders_last_30d": 0,
                "critical_risks": 0,
                "pending_recommendations": 0,
                "last_ingestion_run": None,
                "last_forecast_run": None,
            },
        )

    from sqlalchemy import func as sqlfunc
    fm_count = db.query(sqlfunc.count(FeatureMatrix.id)).scalar() or 0
    latest_feat = db.query(FeatureRun).order_by(FeatureRun.started_at.desc()).first()

    forecast_rows_count = db.query(sqlfunc.count(Forecast.id)).scalar() or 0
    model_metrics_count = db.query(sqlfunc.count(ModelMetric.id)).scalar() or 0
    latest_frun = (
        db.query(ForecastRun)
        .filter(ForecastRun.status == "completed")
        .order_by(ForecastRun.started_at.desc())
        .first()
    )

    latest_wape = None
    if latest_frun:
        mm = (
            db.query(ModelMetric)
            .filter(
                ModelMetric.run_id == latest_frun.id,
                ModelMetric.level == "overall",
            )
            .first()
        )
        if mm:
            latest_wape = mm.wape

    # ML model readiness (Sprint 5)
    latest_ml_mv = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.status == "completed",
            ModelVersion.model_type == "ml_global_regressor",
        )
        .order_by(ModelVersion.created_at.desc())
        .first()
    )
    latest_ml_wape = None
    if latest_ml_mv and latest_ml_mv.metrics_summary_json:
        latest_ml_wape = (
            latest_ml_mv.metrics_summary_json.get("overall", {}).get("wape")
        )

    # Risk counts (Sprint 6)
    latest_risk_run = (
        db.query(StockoutRiskRun)
        .filter(StockoutRiskRun.status == "completed")
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    critical_count = latest_risk_run.critical_count if latest_risk_run else 0
    high_count = latest_risk_run.high_count if latest_risk_run else 0
    medium_count = latest_risk_run.medium_count if latest_risk_run else 0
    low_count = latest_risk_run.low_count if latest_risk_run else 0

    # Estimated lost sales value from latest risk run
    lost_sales_value = None
    if latest_risk_run:
        lost_sales_value = (
            db.query(func.sum(StockoutRisk.lost_sales_value_estimate))
            .filter(StockoutRisk.risk_run_id == latest_risk_run.id)
            .scalar()
        )
        if lost_sales_value is not None:
            lost_sales_value = float(lost_sales_value)

    # Recommendation counts (Sprint 7)
    latest_rec_run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    open_rec_count = 0
    critical_rec_count = 0
    high_rec_count = 0
    total_rec_units = 0.0
    estimated_order_cost = 0.0
    estimated_lost_sales_avoided = 0.0
    if latest_rec_run:
        open_rec_count = (
            db.query(func.count(ReorderRecommendation.id))
            .filter(
                ReorderRecommendation.recommendation_run_id == latest_rec_run.id,
                ReorderRecommendation.status == "open",
            )
            .scalar() or 0
        )
        critical_rec_count = latest_rec_run.critical_count or 0
        high_rec_count = latest_rec_run.high_count or 0
        total_rec_units = float(latest_rec_run.total_recommended_units or 0.0)
        estimated_order_cost = float(latest_rec_run.total_estimated_value or 0.0)
        avoided = (
            db.query(func.sum(ReorderRecommendation.estimated_lost_sales_avoided))
            .filter(ReorderRecommendation.recommendation_run_id == latest_rec_run.id)
            .scalar()
        )
        estimated_lost_sales_avoided = float(avoided or 0.0)

    import os as _os
    return OverviewResponse(
        status="ok",
        data_mode="mock",
        pipeline_ready=True,
        message="Raw data ingested. Run aggregation + feature build to activate forecasting.",
        summary={
            "products": products_count,
            "stores": stores_count,
            "orders": orders_count,
            "feature_rows_count": fm_count,
            "feature_readiness": "ready" if fm_count > 0 else "not_ready",
            "latest_feature_run_status": latest_feat.status if latest_feat else None,
            "latest_forecast_run_status": latest_frun.status if latest_frun else None,
            "latest_baseline_model": latest_frun.model_type if latest_frun else None,
            "latest_baseline_wape": latest_wape,
            "forecast_rows_count": forecast_rows_count,
            "model_metrics_count": model_metrics_count,
            "last_ingestion_run": str(latest_run.started_at) if latest_run else None,
            # ML model readiness fields (honest — null when no ML model trained)
            "latest_ml_model_status": latest_ml_mv.status if latest_ml_mv else None,
            "latest_ml_model_algorithm": latest_ml_mv.algorithm if latest_ml_mv else None,
            "latest_ml_wape": latest_ml_wape,
            "best_baseline_wape": latest_wape,
            "model_artifact_exists": (
                latest_ml_mv.artifact_path is not None
                and _os.path.exists(latest_ml_mv.artifact_path)
            ) if latest_ml_mv else False,
            # Sprint 6: honest risk metrics (null when no risk run has been executed)
            "critical_stockout_count": critical_count,
            "high_stockout_count": high_count,
            "medium_stockout_count": medium_count,
            "low_stockout_count": low_count,
            "estimated_lost_sales_value": lost_sales_value,
            "latest_risk_run_status": latest_risk_run.status if latest_risk_run else None,
            "latest_risk_horizon_days": latest_risk_run.risk_horizon_days if latest_risk_run else None,
            # Sprint 7: honest recommendation metrics (null when no recommendations run)
            "open_recommendation_count": open_rec_count,
            "critical_recommendation_count": critical_rec_count,
            "high_recommendation_count": high_rec_count,
            "total_recommended_units": total_rec_units,
            "estimated_order_cost": estimated_order_cost,
            "estimated_lost_sales_avoided": estimated_lost_sales_avoided,
            "latest_recommendation_run_status": (
                latest_rec_run.status if latest_rec_run else None
            ),
        },
    )


@router.get("/data-health")
def get_data_health(db: Session = Depends(get_db)):
    """
    Data quality report: real persisted counts and validation check statuses.
    """
    products_count   = db.query(func.count(RawProduct.id)).scalar() or 0
    stores_count     = db.query(func.count(RawStore.id)).scalar() or 0
    orders_count     = db.query(func.count(RawOrder.id)).scalar() or 0
    inv_count        = db.query(func.count(RawInventorySnapshot.id)).scalar() or 0
    promos_count     = db.query(func.count(RawPromotion.id)).scalar() or 0
    suppliers_count  = db.query(func.count(RawSupplier.id)).scalar() or 0
    po_count         = db.query(func.count(RawPurchaseOrder.id)).scalar() or 0

    if products_count == 0:
        return {
            "status": "no_data",
            "data_mode": "mock",
            "products_count": 0,
            "stores_count": 0,
            "orders_count": 0,
            "inventory_snapshots_count": 0,
            "promotions_count": 0,
            "suppliers_count": 0,
            "purchase_orders_count": 0,
            "latest_ingestion_run": None,
            "checks": [
                {"name": "data_seeded", "status": "failed",
                 "detail": "No data ingested. Run POST /api/demo/reset."},
            ],
            "message": "No data. Run POST /api/demo/reset to seed the demo dataset.",
        }

    # Latest ingestion run
    latest_run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .first()
    )
    latest_run_info = None
    if latest_run:
        latest_run_info = {
            "run_id":       latest_run.id,
            "status":       latest_run.status,
            "started_at":   str(latest_run.started_at),
            "completed_at": str(latest_run.finished_at) if latest_run.finished_at else None,
        }

    # Latest aggregation run
    latest_agg = (
        db.query(AggregationRun)
        .order_by(AggregationRun.started_at.desc())
        .first()
    )

    # Feature counts
    fm_count = db.query(func.count(FeatureMatrix.id)).scalar() or 0
    latest_feat = (
        db.query(FeatureRun)
        .order_by(FeatureRun.started_at.desc())
        .first()
    )
    latest_feat_info = None
    if latest_feat:
        latest_feat_info = {
            "run_id": latest_feat.id,
            "status": latest_feat.status,
            "rows_created": latest_feat.rows_created or 0,
        }
    latest_agg_info = None
    if latest_agg:
        latest_agg_info = {
            "run_id": latest_agg.id,
            "status": latest_agg.status,
            "started_at": str(latest_agg.started_at),
        }

    # Forecast counts
    forecast_runs_count = db.query(func.count(ForecastRun.id)).scalar() or 0
    forecasts_count     = db.query(func.count(Forecast.id)).scalar() or 0
    mm_count            = db.query(func.count(ModelMetric.id)).scalar() or 0
    latest_frun = (
        db.query(ForecastRun)
        .filter(ForecastRun.status == "completed")
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    latest_frun_info = None
    if latest_frun:
        latest_frun_info = {
            "run_id": latest_frun.id,
            "model_type": latest_frun.model_type,
            "status": latest_frun.status,
            "rows_created": latest_frun.rows_created or 0,
        }

    # ML model counts (Sprint 5)
    model_versions_count = db.query(func.count(ModelVersion.id)).scalar() or 0
    ml_runs_count = (
        db.query(func.count(ForecastRun.id))
        .filter(ForecastRun.model_type == "hist_gradient_boosting")
        .scalar() or 0
    )
    latest_ml_mv = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.status == "completed",
            ModelVersion.model_type == "ml_global_regressor",
        )
        .order_by(ModelVersion.created_at.desc())
        .first()
    )
    latest_ml_mv_info = None
    if latest_ml_mv:
        latest_ml_mv_info = {
            "model_version_id": latest_ml_mv.id,
            "algorithm": latest_ml_mv.algorithm,
            "status": latest_ml_mv.status,
        }

    # Canonical counts
    sales_daily_count = db.query(func.count(SalesDaily.id)).scalar() or 0
    inv_daily_count   = db.query(func.count(InventoryDaily.id)).scalar() or 0
    psd_count         = db.query(func.count(ProductStoreDaily.id)).scalar() or 0

    # Referential integrity check
    orphaned_orders = (
        db.query(func.count(RawOrder.id))
        .filter(~RawOrder.product_id.in_(db.query(RawProduct.id)))
        .scalar() or 0
    )

    # Stockout check
    stockout_count = (
        db.query(func.count(RawInventorySnapshot.id))
        .filter(RawInventorySnapshot.quantity_on_hand == 0)
        .scalar() or 0
    )

    # Recommendation counts (Sprint 7)
    rec_runs_count = db.query(func.count(RecommendationRun.id)).scalar() or 0
    recs_count     = db.query(func.count(ReorderRecommendation.id)).scalar() or 0
    latest_rec_run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    latest_rec_run_info = None
    if latest_rec_run:
        latest_rec_run_info = {
            "run_id": latest_rec_run.id,
            "status": latest_rec_run.status,
            "mode": latest_rec_run.mode,
        }

    # Risk counts (Sprint 6)
    risk_runs_count = db.query(func.count(StockoutRiskRun.id)).scalar() or 0
    risks_count     = db.query(func.count(StockoutRisk.id)).scalar() or 0
    latest_risk_run = (
        db.query(StockoutRiskRun)
        .filter(StockoutRiskRun.status == "completed")
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    latest_risk_run_info = None
    if latest_risk_run:
        latest_risk_run_info = {
            "run_id": latest_risk_run.id,
            "status": latest_risk_run.status,
            "mode": latest_risk_run.mode,
            "as_of_date": str(latest_risk_run.as_of_date) if latest_risk_run.as_of_date else None,
            "rows_created": latest_risk_run.rows_created or 0,
        }

    checks = [
        {"name": "data_seeded", "status": "passed"},
        {"name": "products_present",      "status": "passed", "detail": f"{products_count} products"},
        {"name": "stores_present",        "status": "passed", "detail": f"{stores_count} stores"},
        {"name": "orders_present",        "status": "passed", "detail": f"{orders_count} order lines"},
        {"name": "inventory_present",     "status": "passed", "detail": f"{inv_count} snapshots"},
        {"name": "promotions_present",    "status": "passed" if promos_count > 0 else "warning",
         "detail": f"{promos_count} promotions"},
        {"name": "referential_integrity", "status": "passed" if orphaned_orders == 0 else "failed",
         "detail": f"{orphaned_orders} orphaned order lines"},
        {"name": "stockouts_exist",       "status": "passed" if stockout_count > 0 else "warning",
         "detail": f"{stockout_count} zero-stock snapshots"},
        {"name": "aggregation_run",       "status": "passed" if latest_agg and latest_agg.status == "success" else "warning",
         "detail": f"sales_daily={sales_daily_count}, inventory_daily={inv_daily_count}"},
        {"name": "feature_build",         "status": "passed" if latest_feat and latest_feat.status == "completed" else "warning",
         "detail": f"feature_matrix={fm_count} rows"},
        {"name": "forecast_run", "status": "passed" if latest_frun else "warning",
         "detail": f"forecast_runs={forecast_runs_count}, forecasts={forecasts_count}"},
        {"name": "ml_model", "status": "passed" if latest_ml_mv else "warning",
         "detail": f"model_versions={model_versions_count}, ml_forecast_runs={ml_runs_count}"},
        {"name": "stockout_risk_run", "status": "passed" if latest_risk_run else "warning",
         "detail": f"stockout_risk_runs={risk_runs_count}, stockout_risks={risks_count}"},
        {"name": "recommendation_run", "status": "passed" if latest_rec_run else "warning",
         "detail": f"recommendation_runs={rec_runs_count}, reorder_recommendations={recs_count}"},
    ]

    all_passed = all(c["status"] == "passed" for c in checks)

    return {
        "status":                    "ok" if all_passed else "warning",
        "data_mode":                 "mock",
        "products_count":            products_count,
        "stores_count":              stores_count,
        "orders_count":              orders_count,
        "inventory_snapshots_count": inv_count,
        "promotions_count":          promos_count,
        "suppliers_count":           suppliers_count,
        "purchase_orders_count":     po_count,
        "latest_ingestion_run":      latest_run_info,
        "latest_aggregation_run":    latest_agg_info,
        "canonical_counts": {
            "sales_daily":        sales_daily_count,
            "inventory_daily":    inv_daily_count,
            "product_store_daily": psd_count,
        },
        "feature_counts": {"feature_matrix": fm_count},
        "latest_feature_run": latest_feat_info,
        "forecast_counts": {
            "forecast_runs": forecast_runs_count,
            "forecasts":     forecasts_count,
            "model_metrics": mm_count,
        },
        "latest_forecast_run": latest_frun_info,
        "model_counts": {
            "model_versions": model_versions_count,
            "ml_forecast_runs": ml_runs_count,
        },
        "latest_model_version": latest_ml_mv_info,
        "risk_counts": {
            "stockout_risk_runs": risk_runs_count,
            "stockout_risks": risks_count,
        },
        "latest_stockout_risk_run": latest_risk_run_info,
        "recommendation_counts": {
            "recommendation_runs": rec_runs_count,
            "reorder_recommendations": recs_count,
        },
        "latest_recommendation_run": latest_rec_run_info,
        "checks":  checks,
        "message": "Data health checks complete.",
    }
