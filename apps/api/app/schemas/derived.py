"""
Derived record schemas — computed by the pipeline, never ingested from connectors.

These models represent outputs of aggregation, feature engineering, forecasting,
and recommendation services.  They must never be passed as input to connectors.
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SalesDailyRecord(BaseModel):
    id: str
    product_id: str
    store_id: str
    sale_date: date
    total_units: float
    total_revenue: float
    avg_unit_price: float
    order_count: int
    promotion_active: bool = False
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class InventoryDailyRecord(BaseModel):
    id: str
    product_id: str
    store_id: str
    snapshot_date: date
    quantity_on_hand: float
    quantity_on_order: float
    days_of_supply: Optional[float] = None
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class FeatureRow(BaseModel):
    """A single row in the ML feature matrix."""
    id: str
    product_id: str
    store_id: str
    feature_date: date
    features: dict[str, Any] = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ForecastRecord(BaseModel):
    id: str
    forecast_run_id: str
    product_id: str
    store_id: str
    forecast_date: date
    predicted_units: float
    lower_bound: float
    upper_bound: float
    confidence_level: float = 0.9
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class StockoutRiskRecord(BaseModel):
    id: str
    product_id: str
    store_id: str
    risk_date: date
    stockout_probability: float       # 0–1
    days_until_stockout: float
    current_on_hand: float
    safety_stock_level: float
    risk_tier: str                    # critical / high / medium / low
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ReorderRecommendationRecord(BaseModel):
    id: str
    product_id: str
    store_id: str
    supplier_id: Optional[str] = None
    recommendation_date: date
    recommended_qty: float
    reorder_point: float
    economic_order_qty: float
    expected_delivery_date: Optional[date] = None
    estimated_cost: Optional[float] = None
    rationale: Optional[str] = None
    status: str = "pending"
    computed_at: datetime = Field(default_factory=datetime.utcnow)
