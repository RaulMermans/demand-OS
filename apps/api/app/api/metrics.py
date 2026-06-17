"""
Model metrics API — Sprint 4.

GET /api/model-metrics   — persisted metrics by run / model / level
GET /api/metrics         — scaffold (Sprint 6: active model version metrics)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.models import ModelMetric, ForecastRun
from app.schemas.api import ScaffoldNotReady

router = APIRouter()


@router.get("/model-metrics")
def get_model_metrics(
    model_type: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    run_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return persisted forecast metrics.

    Optional filters: model_type, level (overall/category/store), run_id.
    """
    query = db.query(ModelMetric)

    if run_id:
        query = query.filter(ModelMetric.run_id == run_id)
    elif not run_id:
        # Default: metrics from the latest completed run
        latest_run = (
            db.query(ForecastRun)
            .filter(ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )
        if latest_run:
            query = query.filter(ModelMetric.run_id == latest_run.id)

    if model_type:
        query = query.filter(ModelMetric.model_type == model_type)
    if level:
        query = query.filter(ModelMetric.level == level)

    rows = (
        query
        .order_by(ModelMetric.level, ModelMetric.level_value)
        .limit(limit)
        .all()
    )

    if not rows:
        return {
            "status": "no_metrics",
            "message": "No metrics found. Run POST /api/forecasts/baseline/run first.",
            "metrics": [],
        }

    return {
        "status": "ok",
        "metrics": [
            {
                "id": m.id,
                "run_id": m.run_id,
                "model_type": m.model_type,
                "horizon_days": m.horizon_days,
                "level": m.level,
                "level_value": m.level_value,
                "mae": m.mae,
                "rmse": m.rmse,
                "wape": m.wape,
                "smape": m.smape,
                "bias": m.bias,
                "rows_evaluated": m.rows_evaluated,
                "created_at": str(m.created_at) if m.created_at else None,
            }
            for m in rows
        ],
        "total": len(rows),
    }


@router.get("/metrics")
def get_active_model_metrics():
    """
    Active model version metrics — Sprint 6 placeholder.
    Will query model_metrics for the active ModelVersion once ML training is implemented.
    """
    return ScaffoldNotReady(endpoint="/api/metrics")


@router.get("/metrics/history")
def get_metrics_history():
    """Model metric history across versions — Sprint 6 placeholder."""
    return ScaffoldNotReady(endpoint="/api/metrics/history")
