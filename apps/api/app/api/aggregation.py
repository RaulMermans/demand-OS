"""
Aggregation API — run the aggregation pipeline and query run status.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import AggregationRun, SalesDaily, InventoryDaily, ProductStoreDaily
from app.services.aggregation_service import AggregationService
from app.api.auth import require_api_key

router = APIRouter()


class AggregationRunRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@router.post("/aggregation/run")
def run_aggregation(
    req: AggregationRunRequest = AggregationRunRequest(),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
):
    """
    Trigger a full aggregation pass.
    Uses the full raw data date range when start/end are omitted.
    """
    from app.db.models import RawOrder
    from sqlalchemy import func

    start = req.start_date
    end = req.end_date

    if start is None or end is None:
        row = db.query(func.min(RawOrder.order_date), func.max(RawOrder.order_date)).first()
        if row is None or row[0] is None:
            return {"status": "no_data",
                    "message": "No raw orders found. Run POST /api/demo/reset first."}
        start = start or row[0]
        end = end or row[1]

    svc = AggregationService(db)
    result = svc.run_full_aggregation(start, end)
    return result


@router.get("/aggregation/status")
def aggregation_status(db: Session = Depends(get_db)):
    """Return the status of the most recent aggregation run and canonical table counts."""
    latest = (
        db.query(AggregationRun)
        .order_by(AggregationRun.started_at.desc())
        .first()
    )

    sales_count = db.query(func.count(SalesDaily.id)).scalar() or 0
    inv_count = db.query(func.count(InventoryDaily.id)).scalar() or 0
    psd_count = db.query(func.count(ProductStoreDaily.id)).scalar() or 0

    latest_info = None
    if latest:
        latest_info = {
            "run_id": latest.id,
            "status": latest.status,
            "start_date": str(latest.start_date) if latest.start_date else None,
            "end_date": str(latest.end_date) if latest.end_date else None,
            "started_at": str(latest.started_at),
            "finished_at": str(latest.finished_at) if latest.finished_at else None,
            "records_produced": latest.records_produced or {},
        }

    if latest is None:
        status = "not_run"
    elif latest.status == "success":
        status = "ready"
    elif latest.status == "running":
        status = "running"
    else:
        status = "failed"

    return {
        "status": status,
        "latest_run": latest_info,
        "canonical_counts": {
            "sales_daily": sales_count,
            "inventory_daily": inv_count,
            "product_store_daily": psd_count,
        },
    }
