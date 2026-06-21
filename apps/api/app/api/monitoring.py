"""
Model and data monitoring API.

Endpoints:
  POST /api/monitoring/run     — run monitoring (API key required)
  GET  /api/monitoring/latest  — latest monitoring run
  GET  /api/monitoring/runs    — recent monitoring runs
  GET  /api/monitoring/model   — model drift metrics
  GET  /api/monitoring/data    — data drift metrics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.db.session import get_db
from app.services.monitoring_service import MonitoringService

router = APIRouter()


@router.post("/monitoring/run")
def run_monitoring(
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> dict:
    """Run a monitoring check. API key required when configured."""
    service = MonitoringService(db)
    return service.run()


@router.get("/monitoring/latest")
def get_latest_monitoring(db: Session = Depends(get_db)) -> dict:
    service = MonitoringService(db)
    result = service.get_latest()
    if not result:
        return {
            "has_monitoring_run": False,
            "latest_run": None,
        }
    return {
        "has_monitoring_run": True,
        "latest_run": result,
    }


@router.get("/monitoring/runs")
def get_monitoring_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    service = MonitoringService(db)
    runs = service.get_runs(limit=limit)
    return {"runs": runs, "total": len(runs)}


@router.get("/monitoring/model")
def get_model_metrics(
    run_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    service = MonitoringService(db)
    metrics = service.get_model_metrics(run_id=run_id)
    return {
        "metrics": metrics,
        "total": len(metrics),
        "interpretation": {
            "green": "Relative change <= 10% — healthy",
            "yellow": "Relative change 10–25% — monitor closely",
            "red": "Relative change > 25% — investigate",
            "unknown": "No previous run to compare against",
        },
    }


@router.get("/monitoring/data")
def get_data_metrics(
    run_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    service = MonitoringService(db)
    metrics = service.get_data_metrics(run_id=run_id)
    return {
        "metrics": metrics,
        "total": len(metrics),
        "note": "Data drift uses simple aggregate comparisons. "
                "No complex statistical tests are used in this version.",
    }
