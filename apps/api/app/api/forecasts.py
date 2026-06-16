from fastapi import APIRouter
from app.schemas.api import ScaffoldNotReady

router = APIRouter()


@router.get("/forecasts")
def list_forecasts():
    """
    Return demand forecasts per SKU/store/date.
    Sprint 4 TODO: query forecasts table and return paginated results.
    """
    return ScaffoldNotReady(endpoint="/api/forecasts")


@router.get("/forecasts/{product_id}")
def get_product_forecast(product_id: str):
    """
    Return 28-day demand forecast for a single product across all stores.
    Sprint 4 TODO: query forecasts and return time-series response.
    """
    return ScaffoldNotReady(endpoint=f"/api/forecasts/{product_id}")
