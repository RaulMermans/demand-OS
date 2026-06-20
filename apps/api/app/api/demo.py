"""
Demo API endpoints — seed/reset the synthetic demo dataset + full pipeline orchestration.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService
from app.services.demo_pipeline_service import DemoPipelineService
from app.api.auth import require_api_key

router = APIRouter()


class DemoResetRequest(BaseModel):
    seed: int = 42
    product_count: int = 50
    store_count: int = 5
    history_days: int = 730


class FullPipelineRequest(BaseModel):
    seed: int = 42
    product_count: int = 50
    store_count: int = 5
    history_days: int = 730


def _run_to_dict(run) -> dict:
    return {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "current_step": run.current_step,
        "steps": run.steps_json or [],
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


@router.post("/demo/reset")
def reset_demo(
    req: DemoResetRequest = DemoResetRequest(),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    Clear all existing mock data and regenerate a fresh seeded demo dataset.

    This is the primary way to initialise DemandOS for a demo.
    The operation is idempotent: running it twice with the same seed
    produces the same data.
    """
    end_date   = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=req.history_days - 1)

    config = MockConfig(
        seed=req.seed,
        product_count=req.product_count,
        store_count=req.store_count,
        history_days=req.history_days,
        start_date=start_date,
        end_date=end_date,
    )
    connector = MockCommerceConnector(config)
    service   = IngestionService(connector, db)
    result    = service.reset_and_seed(start_date, end_date)

    return {
        "status":  "ok",
        "message": (
            f"Demo dataset seeded: {req.product_count} products, "
            f"{req.store_count} stores, {req.history_days} days of history."
        ),
        "config": {
            "seed":          req.seed,
            "product_count": req.product_count,
            "store_count":   req.store_count,
            "start_date":    str(start_date),
            "end_date":      str(end_date),
        },
        "ingestion": result,
    }


@router.post("/demo/run-full-pipeline")
def run_full_pipeline(
    req: FullPipelineRequest = FullPipelineRequest(),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    Run the complete DemandOS demo pipeline in one call.

    Stages (in order):
      1. Reset demo data
      2. Aggregation
      3. Feature build
      4. Baseline forecast
      5. ML model training
      6. Planning forecast
      7. Stockout risk
      8. Recommendations

    Stops immediately when any step fails. Returns per-step status.
    A durable DemoPipelineRun record is created and updated throughout.

    API-key protected when DEMANDOS_API_KEY is configured.
    Does not create purchase orders or call external APIs.
    """
    svc = DemoPipelineService(db)
    run = svc.run_full_pipeline(
        seed=req.seed,
        product_count=req.product_count,
        store_count=req.store_count,
        history_days=req.history_days,
    )
    return {
        "status": run.status,
        "message": (
            "Full demo pipeline completed successfully."
            if run.status == "completed"
            else f"Pipeline stopped at step '{run.current_step}': {run.error_message}"
        ),
        "run": _run_to_dict(run),
    }


@router.get("/demo/pipeline-runs")
def list_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all demo pipeline run records, newest first."""
    svc = DemoPipelineService(db)
    runs = svc.get_pipeline_runs(limit=limit)
    return {
        "runs": [_run_to_dict(r) for r in runs],
        "total": len(runs),
    }


@router.get("/demo/pipeline-runs/latest")
def get_latest_pipeline_run(db: Session = Depends(get_db)):
    """Return the most recent demo pipeline run, or null if none exist."""
    svc = DemoPipelineService(db)
    run = svc.get_latest_pipeline_run()
    if run is None:
        return {"run": None, "status": "no_runs"}
    return {"run": _run_to_dict(run), "status": run.status}
