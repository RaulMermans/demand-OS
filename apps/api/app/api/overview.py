from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.db.models import (
    RawProduct, RawStore, RawOrder, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
    IngestionRun, AggregationRun, SalesDaily, InventoryDaily, ProductStoreDaily,
    FeatureMatrix, FeatureRun,
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

    from app.db.models import FeatureMatrix, FeatureRun
    from sqlalchemy import func as sqlfunc
    fm_count = db.query(sqlfunc.count(FeatureMatrix.id)).scalar() or 0
    latest_feat = db.query(FeatureRun).order_by(FeatureRun.started_at.desc()).first()

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
            "critical_risks": 0,
            "pending_recommendations": 0,
            "last_ingestion_run": str(latest_run.started_at) if latest_run else None,
            "last_forecast_run": None,
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

    checks = [
        {"name": "data_seeded",           "status": "passed"},
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
        "checks":  checks,
        "message": "Data health checks complete.",
    }
