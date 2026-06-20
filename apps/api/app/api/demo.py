"""
Demo API endpoints — seed and reset the synthetic demo dataset.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService
from app.api.auth import require_api_key

router = APIRouter()


class DemoResetRequest(BaseModel):
    seed: int = 42
    product_count: int = 50
    store_count: int = 5
    history_days: int = 730


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
