from fastapi import APIRouter
from app.schemas.api import ScaffoldNotReady

router = APIRouter()


@router.get("/metrics")
def get_model_metrics():
    """
    Return model performance metrics (RMSE, MAE, SMAPE, bias, coverage).
    Sprint 6 TODO: query model_metrics table for the active model version.
    """
    return ScaffoldNotReady(endpoint="/api/metrics")


@router.get("/metrics/history")
def get_metrics_history():
    """
    Return model metric history across versions for drift detection.
    Sprint 6 TODO: query model_metrics joined with model_versions.
    """
    return ScaffoldNotReady(endpoint="/api/metrics/history")
