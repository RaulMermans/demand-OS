from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import date
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import IngestionRun
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService
from app.api.auth import require_api_key

router = APIRouter()


class IngestionRequest(BaseModel):
    start_date: date
    end_date: date
    dry_run: bool = False
    seed: int = 42
    products: int = 50
    stores: int = 5


@router.post("/ingestion/run")
def trigger_ingestion(
    req: IngestionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    Run mock ingestion for the given date range.
    Uses MockCommerceConnector with the provided seed/config.
    """
    config = MockConfig(
        seed=req.seed,
        product_count=req.products,
        store_count=req.stores,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    connector = MockCommerceConnector(config)
    service   = IngestionService(connector, db)
    result    = service.run(req.start_date, req.end_date, dry_run=req.dry_run)
    return result


@router.get("/ingestion/runs")
def list_ingestion_runs(limit: int = 20, db: Session = Depends(get_db)):
    """Return recent ingestion runs, most recent first."""
    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "run_id":           r.id,
                "connector":        r.connector,
                "status":           r.status,
                "started_at":       str(r.started_at),
                "completed_at":     str(r.finished_at) if r.finished_at else None,
                "records_ingested": r.records_ingested,
                "metadata":         r.run_metadata or {},
            }
            for r in runs
        ],
        "total": len(runs),
    }
