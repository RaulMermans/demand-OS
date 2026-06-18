"""
Risk API routes — Sprint 6.

POST /api/risks/run                     — run stockout risk engine
GET  /api/risks/runs                    — list all risk runs
GET  /api/risks/latest                  — latest risk run + sample of risk rows
GET  /api/risks                         — ranked risk rows (filtered/sorted)
GET  /api/risks/product/{product_id}    — risk detail for one product across stores
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.models import StockoutRiskRun, StockoutRisk
from app.services.stockout_service import StockoutService, VALID_MODES

router = APIRouter()

# Risk tier ordering for sorting (lower number = higher priority)
_TIER_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RiskRunRequest(BaseModel):
    forecast_run_id: Optional[str] = None
    horizon_days: int = 28
    mode: str = "forward_planning"


# ---------------------------------------------------------------------------
# POST /api/risks/run
# ---------------------------------------------------------------------------

@router.post("/risks/run")
def run_stockout_risk(
    body: RiskRunRequest,
    db: Session = Depends(get_db),
):
    """
    Run the stockout risk engine.

    Selects the best available forecast run (forward_planning preferred),
    reads current inventory, inbound POs, and supplier lead times,
    then computes risk scores and persists results.
    """
    if body.mode not in VALID_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode '{body.mode}'. Allowed: {sorted(VALID_MODES)}",
        )
    svc = StockoutService(db)
    result = svc.run_stockout_risk(
        forecast_run_id=body.forecast_run_id,
        horizon_days=body.horizon_days,
        mode=body.mode,
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=422, detail=result.get("error", "Risk run failed"))
    return result


# ---------------------------------------------------------------------------
# GET /api/risks/runs
# ---------------------------------------------------------------------------

@router.get("/risks/runs")
def list_risk_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all stockout risk runs, newest first."""
    runs = (
        db.query(StockoutRiskRun)
        .order_by(StockoutRiskRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [_run_dict(r) for r in runs],
        "total": len(runs),
    }


# ---------------------------------------------------------------------------
# GET /api/risks/latest
# ---------------------------------------------------------------------------

@router.get("/risks/latest")
def get_latest_risk(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return the latest completed risk run and a bounded sample of risk rows."""
    run = (
        db.query(StockoutRiskRun)
        .filter(StockoutRiskRun.status == "completed")
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    if not run:
        return {
            "status": "no_risk_run",
            "message": "No completed risk run. POST /api/risks/run first.",
            "run": None,
            "sample": [],
        }

    sample = (
        db.query(StockoutRisk)
        .filter(StockoutRisk.risk_run_id == run.id)
        .order_by(
            StockoutRisk.risk_score.desc().nullslast(),
            StockoutRisk.lost_sales_value_estimate.desc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    return {
        "status": "ok",
        "run": _run_dict(run),
        "sample": [_risk_dict(r) for r in sample],
        "sample_size": len(sample),
    }


# ---------------------------------------------------------------------------
# GET /api/risks
# ---------------------------------------------------------------------------

@router.get("/risks")
def list_stockout_risks(
    risk_tier: Optional[str] = Query(default=None),
    store_id: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Return ranked stockout risk rows from the latest completed run.

    Sort order: critical → high → medium → low → unknown,
                then by lost_sales_value_estimate descending,
                then by risk_score descending.

    Query params:
      risk_tier  — filter to specific tier (critical/high/medium/low/unknown)
      store_id   — filter to specific store
      category   — filter to specific category
      limit      — max rows returned (default 100)
    """
    run = (
        db.query(StockoutRiskRun)
        .filter(StockoutRiskRun.status == "completed")
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    if not run:
        return {
            "status": "no_risk_run",
            "message": "No completed risk run. POST /api/risks/run first.",
            "run_id": None,
            "rows": [],
            "total": 0,
        }

    query = db.query(StockoutRisk).filter(StockoutRisk.risk_run_id == run.id)

    if risk_tier:
        query = query.filter(StockoutRisk.risk_tier == risk_tier)
    if store_id:
        query = query.filter(StockoutRisk.store_id == store_id)
    if category:
        query = query.filter(StockoutRisk.category == category)

    # Tier ordering via CASE expression
    tier_order = case(
        (StockoutRisk.risk_tier == "critical", 0),
        (StockoutRisk.risk_tier == "high", 1),
        (StockoutRisk.risk_tier == "medium", 2),
        (StockoutRisk.risk_tier == "low", 3),
        else_=4,
    )

    rows = (
        query
        .order_by(
            tier_order,
            StockoutRisk.lost_sales_value_estimate.desc().nullslast(),
            StockoutRisk.risk_score.desc().nullslast(),
        )
        .limit(limit)
        .all()
    )

    return {
        "status": "ok",
        "run_id": run.id,
        "mode": run.mode,
        "as_of_date": str(run.as_of_date) if run.as_of_date else None,
        "rows": [_risk_dict(r) for r in rows],
        "total": len(rows),
        "risk_counts": {
            "critical": run.critical_count or 0,
            "high": run.high_count or 0,
            "medium": run.medium_count or 0,
            "low": run.low_count or 0,
            "unknown": run.unknown_count or 0,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/risks/product/{product_id}
# ---------------------------------------------------------------------------

@router.get("/risks/product/{product_id}")
def get_product_risk(
    product_id: str,
    run_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Return risk details for a product across all stores from the latest risk run."""
    if run_id:
        target_run_id = run_id
    else:
        run = (
            db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )
        if not run:
            return {
                "status": "no_risk_run",
                "product_id": product_id,
                "rows": [],
            }
        target_run_id = run.id

    rows = (
        db.query(StockoutRisk)
        .filter(
            StockoutRisk.risk_run_id == target_run_id,
            StockoutRisk.product_id == product_id,
        )
        .order_by(StockoutRisk.risk_score.desc().nullslast())
        .all()
    )

    return {
        "status": "ok",
        "product_id": product_id,
        "run_id": target_run_id,
        "rows": [_risk_dict(r) for r in rows],
        "total": len(rows),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_dict(r: StockoutRiskRun) -> dict:
    return {
        "run_id": r.id,
        "mode": r.mode,
        "status": r.status,
        "started_at": str(r.started_at) if r.started_at else None,
        "completed_at": str(r.completed_at) if r.completed_at else None,
        "as_of_date": str(r.as_of_date) if r.as_of_date else None,
        "risk_horizon_days": r.risk_horizon_days,
        "rows_created": r.rows_created or 0,
        "risk_counts": {
            "critical": r.critical_count or 0,
            "high": r.high_count or 0,
            "medium": r.medium_count or 0,
            "low": r.low_count or 0,
            "unknown": r.unknown_count or 0,
        },
        "source_forecast_run_id": r.source_forecast_run_id,
        "error_message": r.error_message,
    }


def _risk_dict(r: StockoutRisk) -> dict:
    return {
        "id": r.id,
        "risk_run_id": r.risk_run_id,
        "as_of_date": str(r.as_of_date) if r.as_of_date else None,
        "product_id": r.product_id,
        "store_id": r.store_id,
        "category": r.category,
        "supplier_id": r.supplier_id,
        "forecast_run_id": r.forecast_run_id,
        "model_type": r.model_type,
        "forecast_horizon_days": r.forecast_horizon_days,
        "current_on_hand_units": r.current_on_hand_units,
        "current_available_units": r.current_available_units,
        "inbound_units_within_horizon": r.inbound_units_within_horizon,
        "supplier_lead_time_days": r.supplier_lead_time_days,
        "supplier_reliability_score": r.supplier_reliability_score,
        "forecast_demand_p50": r.forecast_demand_p50,
        "forecast_demand_p90": r.forecast_demand_p90,
        "average_daily_forecast": r.average_daily_forecast,
        "projected_end_inventory_p50": r.projected_end_inventory_p50,
        "projected_end_inventory_p90": r.projected_end_inventory_p90,
        "days_of_supply": r.days_of_supply,
        "days_until_stockout": r.days_until_stockout,
        "expected_stockout_date": str(r.expected_stockout_date) if r.expected_stockout_date else None,
        "safety_stock_units": r.safety_stock_units,
        "inventory_coverage_ratio": r.inventory_coverage_ratio,
        "lost_sales_units_estimate": r.lost_sales_units_estimate,
        "lost_sales_value_estimate": r.lost_sales_value_estimate,
        "risk_score": r.risk_score,
        "risk_tier": r.risk_tier,
        "risk_reason": r.risk_reason,
        "created_at": str(r.created_at) if r.created_at else None,
    }
