"""
Reorder Recommendation API — Sprint 7.

Endpoints:
  POST  /api/recommendations/run              — generate recommendations from a risk run
  GET   /api/recommendations/runs             — list all recommendation runs
  GET   /api/recommendations/latest           — latest completed recommendation run
  GET   /api/recommendations                  — ranked/filtered recommendation list
  GET   /api/recommendations/product/{pid}    — recommendations for one product
  PATCH /api/recommendations/{id}/status      — update recommendation status (no side effects)

Safety boundary:
  - approved_internal means approved inside DemandOS only.
  - No purchase orders are created. No external APIs are called.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import RecommendationRun, ReorderRecommendation
from app.services.recommendation_service import VALID_STATUS
from app.services.recommendation_service import RecommendationService

router = APIRouter()

_URGENCY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RecommendationRunRequest(BaseModel):
    risk_run_id: Optional[str] = None
    include_low_risk: bool = False


class RecommendationStatusUpdate(BaseModel):
    status: str
    reviewed_by: Optional[str] = None
    review_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rec_to_dict(r: ReorderRecommendation) -> dict:
    return {
        "id": r.id,
        "recommendation_run_id": r.recommendation_run_id,
        "source_risk_run_id": r.source_risk_run_id,
        "source_risk_id": r.source_risk_id,
        "as_of_date": str(r.as_of_date) if r.as_of_date else None,
        "product_id": r.product_id,
        "store_id": r.store_id,
        "category": r.category,
        "supplier_id": r.supplier_id,
        "risk_tier": r.risk_tier,
        "risk_score": r.risk_score,
        "expected_stockout_date": str(r.expected_stockout_date) if r.expected_stockout_date else None,
        "days_until_stockout": r.days_until_stockout,
        "current_available_units": r.current_available_units,
        "inbound_units_within_horizon": r.inbound_units_within_horizon,
        "inventory_position": r.inventory_position,
        "supplier_lead_time_days": r.supplier_lead_time_days,
        "supplier_reliability_score": r.supplier_reliability_score,
        "forecast_demand_p50": r.forecast_demand_p50,
        "lead_time_demand_units": r.lead_time_demand_units,
        "safety_stock_units": r.safety_stock_units,
        "reorder_point_units": r.reorder_point_units,
        "recommended_units": r.recommended_units,
        "recommended_units_rounded": r.recommended_units_rounded,
        "min_order_quantity": r.min_order_quantity,
        "order_multiple": r.order_multiple,
        "estimated_order_cost": r.estimated_order_cost,
        "estimated_lost_sales_value": r.estimated_lost_sales_value,
        "estimated_lost_sales_avoided": r.estimated_lost_sales_avoided,
        "urgency": r.urgency,
        "recommendation_reason": r.recommendation_reason,
        "confidence_level": r.confidence_level,
        "status": r.status,
        "reviewed_at": str(r.reviewed_at) if r.reviewed_at else None,
        "reviewed_by": r.reviewed_by,
        "review_note": r.review_note,
        "created_at": str(r.created_at) if r.created_at else None,
        "updated_at": str(r.updated_at) if r.updated_at else None,
    }


def _sort_key(r: ReorderRecommendation):
    urgency_rank = _URGENCY_RANK.get(r.urgency or "low", 3)
    lost_avoided = -(r.estimated_lost_sales_avoided or 0.0)
    risk_score = -(r.risk_score or 0.0)
    return (urgency_rank, lost_avoided, risk_score)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/recommendations/run")
def run_recommendations(
    body: RecommendationRunRequest,
    db: Session = Depends(get_db),
):
    """
    Generate reorder recommendations from a completed stockout risk run.

    Uses latest forward_planning risk run by default.
    Recommendation-only: no purchase orders or external calls.
    """
    svc = RecommendationService(db)
    result = svc.run_reorder_recommendations(
        risk_run_id=body.risk_run_id,
        include_low_risk=body.include_low_risk,
    )
    return result


@router.get("/recommendations/runs")
def list_recommendation_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all recommendation runs, most recent first."""
    runs = (
        db.query(RecommendationRun)
        .order_by(RecommendationRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "run_id": r.id,
                "source_risk_run_id": r.source_risk_run_id,
                "mode": r.mode,
                "status": r.status,
                "as_of_date": str(r.as_of_date) if r.as_of_date else None,
                "started_at": str(r.started_at) if r.started_at else None,
                "completed_at": str(r.completed_at) if r.completed_at else None,
                "rows_created": r.rows_created,
                "critical_count": r.critical_count,
                "high_count": r.high_count,
                "medium_count": r.medium_count,
                "low_count": r.low_count,
                "total_recommended_units": r.total_recommended_units,
                "total_estimated_value": r.total_estimated_value,
            }
            for r in runs
        ],
        "total": len(runs),
    }


@router.get("/recommendations/latest")
def get_latest_recommendation_run(db: Session = Depends(get_db)):
    """Return the latest completed recommendation run and its rows."""
    run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    if run is None:
        return {
            "status": "no_data",
            "message": "No completed recommendation run found. Run POST /api/recommendations/run.",
            "run": None,
            "recommendations": [],
        }

    rows = (
        db.query(ReorderRecommendation)
        .filter(ReorderRecommendation.recommendation_run_id == run.id)
        .all()
    )
    rows_sorted = sorted(rows, key=_sort_key)

    return {
        "status": "ok",
        "run": {
            "run_id": run.id,
            "source_risk_run_id": run.source_risk_run_id,
            "mode": run.mode,
            "status": run.status,
            "as_of_date": str(run.as_of_date) if run.as_of_date else None,
            "rows_created": run.rows_created,
            "critical_count": run.critical_count,
            "high_count": run.high_count,
            "medium_count": run.medium_count,
            "low_count": run.low_count,
            "total_recommended_units": run.total_recommended_units,
            "total_estimated_value": run.total_estimated_value,
        },
        "recommendations": [_rec_to_dict(r) for r in rows_sorted],
    }


@router.get("/recommendations")
def list_recommendations(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    risk_tier: Optional[str] = None,
    store_id: Optional[str] = None,
    category: Optional[str] = None,
    supplier_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    Return ranked recommendation rows from the latest completed run.

    Sort order: critical → high → medium → low,
    then estimated_lost_sales_avoided descending,
    then risk_score descending.
    """
    run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    if run is None:
        return {"recommendations": [], "total": 0, "returned": 0, "limit": limit, "offset": offset, "run_id": None}

    query = db.query(ReorderRecommendation).filter(
        ReorderRecommendation.recommendation_run_id == run.id
    )
    if status:
        query = query.filter(ReorderRecommendation.status == status)
    if urgency:
        query = query.filter(ReorderRecommendation.urgency == urgency)
    if risk_tier:
        query = query.filter(ReorderRecommendation.risk_tier == risk_tier)
    if store_id:
        query = query.filter(ReorderRecommendation.store_id == store_id)
    if category:
        query = query.filter(ReorderRecommendation.category == category)
    if supplier_id:
        query = query.filter(ReorderRecommendation.supplier_id == supplier_id)

    all_rows = query.all()
    all_rows_sorted = sorted(all_rows, key=_sort_key)
    paginated = all_rows_sorted[offset: offset + limit]

    return {
        "recommendations": [_rec_to_dict(r) for r in paginated],
        "total": len(all_rows),
        "returned": len(paginated),
        "limit": limit,
        "offset": offset,
        "run_id": run.id,
    }


@router.get("/recommendations/product/{product_id}")
def get_product_recommendations(
    product_id: str,
    db: Session = Depends(get_db),
):
    """Return recommendations for a single product across all stores."""
    run = (
        db.query(RecommendationRun)
        .filter(RecommendationRun.status == "completed")
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    if run is None:
        return {"product_id": product_id, "recommendations": [], "run_id": None}

    rows = (
        db.query(ReorderRecommendation)
        .filter(
            ReorderRecommendation.recommendation_run_id == run.id,
            ReorderRecommendation.product_id == product_id,
        )
        .all()
    )
    rows_sorted = sorted(rows, key=_sort_key)

    return {
        "product_id": product_id,
        "run_id": run.id,
        "recommendations": [_rec_to_dict(r) for r in rows_sorted],
    }


@router.patch("/recommendations/{recommendation_id}/status")
def update_recommendation_status(
    recommendation_id: str,
    body: RecommendationStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update recommendation status (reviewed, approved_internal, ignored, resolved).

    Safety boundary:
    - approved_internal means approved inside DemandOS only.
    - This endpoint NEVER creates a purchase order.
    - This endpoint NEVER calls external APIs or supplier systems.
    """
    if body.status not in VALID_STATUS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid status '{body.status}'. "
                f"Must be one of: {sorted(VALID_STATUS)}."
            ),
        )

    rec = db.query(ReorderRecommendation).filter(
        ReorderRecommendation.id == recommendation_id
    ).first()
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found.")

    rec.status = body.status
    rec.reviewed_by = body.reviewed_by
    rec.review_note = body.review_note
    if body.status in {"reviewed", "approved_internal", "ignored", "resolved"}:
        rec.reviewed_at = datetime.utcnow()
    rec.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rec)

    return {
        "status": "updated",
        "recommendation_id": recommendation_id,
        "new_status": rec.status,
        "reviewed_by": rec.reviewed_by,
        "reviewed_at": str(rec.reviewed_at) if rec.reviewed_at else None,
        "note": "Recommendation updated. No purchase order created. No external action taken.",
    }
