"""
Raw operational record schemas (Pydantic v2).

These models represent data exactly as it arrives from a commerce system —
no feature engineering, no aggregation, no ML scoring.

Forbidden fields (must never appear here):
  lag_7d, lag_14d, rolling_mean_*, rolling_std_*, forecast, predicted_units,
  risk_score, stockout_probability, days_until_stockout, recommended_reorder,
  safety_stock, reorder_point, economic_order_qty, demand_signal, anomaly_flag.

Those values are computed downstream by the pipeline services.
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class RawProduct(BaseModel):
    id: str
    external_id: str
    sku: str
    name: str
    category: Optional[str] = None
    brand: Optional[str] = None
    supplier_id: Optional[str] = None
    unit_cost: Optional[float] = None
    unit_price: Optional[float] = None
    lead_time_days: Optional[int] = None
    is_active: bool = True
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


class RawStore(BaseModel):
    id: str
    external_id: str
    name: str
    region: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    channel: Optional[str] = None
    is_active: bool = True
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


class RawOrderLine(BaseModel):
    id: str
    external_order_id: str
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    ordered_at: datetime
    order_date: date
    quantity: float
    unit_price: float
    discount_amount: float = 0.0
    currency: str = "USD"
    status: Optional[str] = None
    promotion_id: Optional[str] = None
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


class RawInventorySnapshot(BaseModel):
    id: str
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    snapshot_date: date
    quantity_on_hand: float
    quantity_on_order: float = 0.0
    quantity_reserved: float = 0.0
    warehouse_location: Optional[str] = None
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


class RawPromotion(BaseModel):
    id: str
    external_id: str
    name: Optional[str] = None
    promotion_type: Optional[str] = None
    discount_pct: float = 0.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    applicable_skus: list[str] = Field(default_factory=list)
    applicable_stores: list[str] = Field(default_factory=list)
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


class RawSupplier(BaseModel):
    id: str
    external_id: str
    name: str
    country: Optional[str] = None
    lead_time_days_min: Optional[int] = None
    lead_time_days_max: Optional[int] = None
    reliability_score: Optional[float] = None
    contact_email: Optional[str] = None
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


class RawPurchaseOrder(BaseModel):
    id: str
    external_po_id: str
    supplier_id: Optional[str] = None
    product_id: Optional[str] = None
    store_id: Optional[str] = None
    ordered_at: datetime
    expected_delivery_date: Optional[date] = None
    quantity_ordered: float
    unit_cost: Optional[float] = None
    status: Optional[str] = None
    source_connector: str
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: Optional[dict[str, Any]] = None

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Sentinel — all raw schemas registered here for automated field guard tests.
# ---------------------------------------------------------------------------
ALL_RAW_SCHEMAS = [
    RawProduct,
    RawStore,
    RawOrderLine,
    RawInventorySnapshot,
    RawPromotion,
    RawSupplier,
    RawPurchaseOrder,
]

# Fields that must never appear in raw schemas (added by the pipeline, not by connectors)
FORBIDDEN_DERIVED_FIELDS = {
    "lag_7d", "lag_14d", "lag_28d",
    "rolling_mean_7d", "rolling_mean_14d", "rolling_mean_28d",
    "rolling_std_7d", "rolling_std_14d",
    "forecast", "predicted_units",
    "risk_score", "stockout_probability", "days_until_stockout",
    "recommended_reorder", "safety_stock", "reorder_point",
    "economic_order_qty", "demand_signal", "anomaly_flag",
}
