from fastapi import APIRouter
from app.schemas.api import ScaffoldNotReady

router = APIRouter()


@router.get("/recommendations")
def list_recommendations():
    """
    Return pending reorder recommendations.
    Sprint 5 TODO: query reorder_recommendations table, return sorted by urgency.
    """
    return ScaffoldNotReady(endpoint="/api/recommendations")


@router.get("/recommendations/{product_id}")
def get_product_recommendation(product_id: str):
    """
    Return reorder recommendation detail for a single product.
    Sprint 5 TODO: include EOQ, ROP, supplier info, estimated delivery date.
    """
    return ScaffoldNotReady(endpoint=f"/api/recommendations/{product_id}")
