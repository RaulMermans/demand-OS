"""
Features API — build the feature matrix and query its status.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import FeatureMatrix, FeatureRun
from app.services.feature_service import FeatureService

router = APIRouter()


class FeatureBuildRequest(BaseModel):
    source_aggregation_run_id: Optional[str] = None
    max_lag_days: int = 28


@router.post("/features/build")
def build_features(req: FeatureBuildRequest = FeatureBuildRequest(),
                   db: Session = Depends(get_db)):
    """
    Run the feature engineering pipeline.
    Reads product_store_daily; writes to feature_matrix.
    Idempotent: clears feature_matrix before reinserting.
    """
    svc = FeatureService(db)
    return svc.build_feature_matrix(
        source_aggregation_run_id=req.source_aggregation_run_id,
        max_lag_days=req.max_lag_days,
    )


@router.get("/features/status")
def features_status(db: Session = Depends(get_db)):
    """Return status of the most recent feature run and feature_matrix counts."""
    latest = (
        db.query(FeatureRun)
        .order_by(FeatureRun.started_at.desc())
        .first()
    )

    fm_count = db.query(func.count(FeatureMatrix.id)).scalar() or 0

    latest_info = None
    if latest:
        latest_info = {
            "run_id": latest.id,
            "status": latest.status,
            "started_at": str(latest.started_at),
            "completed_at": str(latest.completed_at) if latest.completed_at else None,
            "rows_created": latest.rows_created or 0,
            "date_min": str(latest.date_min) if latest.date_min else None,
            "date_max": str(latest.date_max) if latest.date_max else None,
            "checks": latest.checks_json or [],
        }

    if latest is None:
        status = "not_run"
    elif latest.status == "completed":
        status = "ready"
    elif latest.status == "running":
        status = "running"
    else:
        status = "failed"

    return {
        "status": status,
        "feature_rows": fm_count,
        "latest_run": latest_info,
    }


@router.get("/features/sample")
def features_sample(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """Return a small bounded sample of feature_matrix rows for debugging."""
    rows = (
        db.query(FeatureMatrix)
        .order_by(FeatureMatrix.date, FeatureMatrix.product_id, FeatureMatrix.store_id)
        .limit(limit)
        .all()
    )

    if not rows:
        return {"status": "empty", "rows": [], "total_in_db": 0}

    total = db.query(func.count(FeatureMatrix.id)).scalar() or 0

    return {
        "status": "ok",
        "sample_size": len(rows),
        "total_in_db": total,
        "rows": [
            {
                "id": r.id, "date": str(r.date),
                "product_id": r.product_id, "store_id": r.store_id,
                "target_units_sold": r.target_units_sold,
                "lag_units_7d": r.lag_units_7d,
                "rolling_units_mean_7d": r.rolling_units_mean_7d,
                "day_of_week": r.day_of_week,
                "promo_active": r.promo_active,
                "discount_pct": r.discount_pct,
                "available_units": r.available_units,
                "days_of_supply": r.days_of_supply,
                "days_since_launch": r.days_since_launch,
                "product_age_bucket": r.product_age_bucket,
                "retail_price": r.retail_price,
                "gross_margin_pct": r.gross_margin_pct,
                "category": r.category,
                "store_channel": r.store_channel,
            }
            for r in rows
        ],
    }
