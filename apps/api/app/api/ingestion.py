from fastapi import APIRouter
from pydantic import BaseModel
from datetime import date
from app.schemas.api import ScaffoldNotReady

router = APIRouter()


class IngestionRequest(BaseModel):
    start_date: date
    end_date: date
    dry_run: bool = True


@router.post("/ingest")
def trigger_ingestion(req: IngestionRequest):
    """
    Trigger a data ingestion run from the active connector.
    Sprint 1 TODO: wire IngestionService, return real record counts.
    """
    return ScaffoldNotReady(endpoint="/api/ingest").model_dump() | {
        "start_date": str(req.start_date),
        "end_date": str(req.end_date),
        "dry_run": req.dry_run,
    }
