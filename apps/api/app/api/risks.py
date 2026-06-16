from fastapi import APIRouter
from app.schemas.api import ScaffoldNotReady

router = APIRouter()


@router.get("/risks")
def list_stockout_risks():
    """
    Return stockout risk scores per SKU/store.
    Sprint 5 TODO: query stockout_risks table, filter by risk_tier, return list.
    """
    return ScaffoldNotReady(endpoint="/api/risks")


@router.get("/risks/{product_id}")
def get_product_risk(product_id: str):
    """
    Return stockout risk detail for a single product.
    Sprint 5 TODO: return risk timeline and contributing factors.
    """
    return ScaffoldNotReady(endpoint=f"/api/risks/{product_id}")
