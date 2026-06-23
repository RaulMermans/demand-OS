"""
Analytics cockpit API routes — Sprint 16.

All endpoints are read-only. No DB mutations.
"""

from typing import Optional, Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analytics_cockpit_service import AnalyticsCockpitService
from app.schemas.analytics import (
    CockpitResponse,
    InventoryTrendResponse,
    RiskDriversResponse,
    ReorderQueueResponse,
    ExecutiveSummaryResponse,
)

router = APIRouter(prefix="/analytics")

ALLOWED_DAYS = {7, 30, 60, 90}


@router.get("/cockpit", response_model=CockpitResponse)
def get_cockpit(db: Session = Depends(get_db)):
    """Executive analytics cockpit — computed KPIs from the full pipeline."""
    return AnalyticsCockpitService(db).get_cockpit()


@router.get("/inventory-trend", response_model=InventoryTrendResponse)
def get_inventory_trend(
    product_id: Optional[str] = Query(None),
    store_id: Optional[str] = Query(None),
    days: int = Query(30),
    db: Session = Depends(get_db),
):
    """
    Inventory on-hand trend with forecasted demand, reorder point, and safety stock.

    Supported `days` values: 7, 30, 60, 90. Defaults to 30 when an invalid value is given.
    """
    safe_days = days if days in ALLOWED_DAYS else 30
    return AnalyticsCockpitService(db).get_inventory_trend(
        product_id=product_id,
        store_id=store_id,
        days=safe_days,
    )


@router.get("/risk-drivers", response_model=RiskDriversResponse)
def get_risk_drivers(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Rule-based risk driver explanations for the top-ranked product/store risks.

    Drivers indicate contributing factors, not guaranteed causal relationships.
    """
    return AnalyticsCockpitService(db).get_risk_drivers(limit=limit)


@router.get("/reorder-queue", response_model=ReorderQueueResponse)
def get_reorder_queue(db: Session = Depends(get_db)):
    """
    Open reorder recommendations formatted as a decision queue.

    Sorted by urgency, risk tier, and estimated lost sales.
    No purchase orders are created. Internal review guidance only.
    """
    return AnalyticsCockpitService(db).get_reorder_queue()


@router.get("/executive-summary", response_model=ExecutiveSummaryResponse)
def get_executive_summary(db: Session = Depends(get_db)):
    """
    Business-readable executive summary derived from the analytics cockpit.

    Uses computed values only — no hardcoded metrics.
    """
    return AnalyticsCockpitService(db).get_executive_summary()
