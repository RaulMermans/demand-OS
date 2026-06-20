"""
Model registry API routes — Sprint 5.

POST /api/models/train        — train ML forecaster + persist results
GET  /api/models/versions     — list all model registry entries
GET  /api/models/latest       — latest completed ML model version
GET  /api/models/compare      — baseline vs ML comparison
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.models import ForecastRun, ModelMetric, ModelVersion
from app.services.training_service import TrainingService
from app.api.auth import require_api_key

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TrainRequest(BaseModel):
    algorithm: str = "hist_gradient_boosting"
    horizon_days: int = 28
    backtest_days: int = 56
    source_feature_run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /api/models/train
# ---------------------------------------------------------------------------

@router.post("/models/train")
def train_model(
    body: TrainRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    Train an ML demand forecasting model.

    Reads from feature_matrix, trains a HistGradientBoostingRegressor,
    persists forecast rows + metrics + model version + artifact.
    """
    if body.algorithm != "hist_gradient_boosting":
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported algorithm '{body.algorithm}'. "
                   "Only 'hist_gradient_boosting' is available in Sprint 5.",
        )

    svc = TrainingService(db)
    result = svc.train_ml_forecaster(
        algorithm=body.algorithm,
        horizon_days=body.horizon_days,
        backtest_days=body.backtest_days,
        source_feature_run_id=body.source_feature_run_id,
    )
    return result


# ---------------------------------------------------------------------------
# GET /api/models/versions
# ---------------------------------------------------------------------------

@router.get("/models/versions")
def list_model_versions(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all model registry entries, newest first."""
    versions = (
        db.query(ModelVersion)
        .order_by(ModelVersion.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "versions": [_version_dict(v) for v in versions],
        "total": len(versions),
    }


# ---------------------------------------------------------------------------
# GET /api/models/latest
# ---------------------------------------------------------------------------

@router.get("/models/latest")
def get_latest_model(db: Session = Depends(get_db)):
    """Return the latest completed ML model version."""
    mv = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.status == "completed",
            ModelVersion.model_type == "ml_global_regressor",
        )
        .order_by(ModelVersion.created_at.desc())
        .first()
    )
    if not mv:
        return {
            "status": "no_model",
            "message": "No completed ML model. POST /api/models/train first.",
            "model_version": None,
        }
    return {
        "status": "ok",
        "model_version": _version_dict(mv),
        "artifact_exists": mv.artifact_path is not None and os.path.exists(mv.artifact_path),
    }


# ---------------------------------------------------------------------------
# GET /api/models/compare
# ---------------------------------------------------------------------------

@router.get("/models/compare")
def compare_models(db: Session = Depends(get_db)):
    """
    Return baseline vs ML comparison.

    Finds the latest completed ML run and the best completed baseline run
    (lowest overall WAPE) and reports the delta.
    """
    # Latest ML run
    ml_run = (
        db.query(ForecastRun)
        .filter(
            ForecastRun.model_type == "hist_gradient_boosting",
            ForecastRun.status == "completed",
        )
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    if not ml_run:
        return {
            "status": "no_ml_model",
            "message": "No completed ML model run. POST /api/models/train first.",
        }

    ml_metric = (
        db.query(ModelMetric)
        .filter(
            ModelMetric.run_id == ml_run.id,
            ModelMetric.level == "overall",
        )
        .first()
    )
    ml_wape = ml_metric.wape if ml_metric else None

    # Best baseline
    baseline_types = ["seasonal_naive", "moving_average_7d", "moving_average_28d"]
    best_baseline_run = None
    best_baseline_wape = None

    for bt in baseline_types:
        brun = (
            db.query(ForecastRun)
            .filter(ForecastRun.model_type == bt, ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )
        if brun is None:
            continue
        bmm = (
            db.query(ModelMetric)
            .filter(ModelMetric.run_id == brun.id, ModelMetric.level == "overall")
            .first()
        )
        if bmm and bmm.wape is not None:
            if best_baseline_wape is None or bmm.wape < best_baseline_wape:
                best_baseline_wape = bmm.wape
                best_baseline_run = brun

    if best_baseline_run is None:
        return {
            "status": "no_baseline",
            "ml_run_id": ml_run.id,
            "ml_wape": ml_wape,
            "message": "No completed baseline runs to compare against.",
        }

    wape_delta = None
    ml_won = None
    if ml_wape is not None and best_baseline_wape is not None:
        wape_delta = round(ml_wape - best_baseline_wape, 6)
        ml_won = ml_wape < best_baseline_wape

    return {
        "status": "ok",
        "ml_run_id": ml_run.id,
        "ml_model_type": ml_run.model_type,
        "ml_wape": ml_wape,
        "best_baseline_run_id": best_baseline_run.id,
        "best_baseline_model_type": best_baseline_run.model_type,
        "best_baseline_wape": best_baseline_wape,
        "wape_delta": wape_delta,
        "ml_won_against_baseline": ml_won,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _version_dict(v: ModelVersion) -> dict:
    return {
        "model_version_id": v.id,
        "model_name": v.model_name,
        "algorithm": v.algorithm,
        "model_type": v.model_type,
        "status": v.status,
        "trained_at": str(v.trained_at) if v.trained_at else None,
        "training_start_date": str(v.training_start_date) if v.training_start_date else None,
        "training_end_date": str(v.training_end_date) if v.training_end_date else None,
        "test_start_date": str(v.test_start_date) if v.test_start_date else None,
        "test_end_date": str(v.test_end_date) if v.test_end_date else None,
        "artifact_path": v.artifact_path,
        "metrics_summary": v.metrics_summary_json,
        "config": v.config_json,
        "feature_columns": v.feature_columns_json,
        "created_at": str(v.created_at) if v.created_at else None,
    }
