"""
Analytics cockpit schemas — Sprint 16.

All schemas are read-only outputs. No derived field is ever an input.
"""

from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# /api/analytics/cockpit
# ---------------------------------------------------------------------------

class DatasetKpis(BaseModel):
    products: int
    stores: int
    sku_store_combinations: int
    orders: int
    inventory_snapshots: int


class InventoryKpis(BaseModel):
    total_inventory_units: Optional[float]
    estimated_inventory_value: Optional[float]
    inventory_value_method: str  # "unit_cost" or "unit_price"
    stockout_risk_percent: Optional[float]
    at_risk_sku_stores: int


class ForecastingKpis(BaseModel):
    latest_model: Optional[str]
    latest_wape: Optional[float]
    forecast_quality_label: str  # Strong / Directional / Weak / No model
    forecast_rows: int
    interpretation: str


class RiskKpis(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    estimated_lost_sales: Optional[float]


class RecommendationKpis(BaseModel):
    open: int
    estimated_order_cost: Optional[float]
    estimated_lost_sales_addressed: Optional[float]


class PipelineStatus(BaseModel):
    data_seeded: str   # "ready" / "pending"
    features: str
    forecasts: str
    risks: str
    recommendations: str


class CockpitResponse(BaseModel):
    status: str
    generated_at: datetime
    dataset: DatasetKpis
    inventory: InventoryKpis
    forecasting: ForecastingKpis
    risk: RiskKpis
    recommendations: RecommendationKpis
    pipeline: PipelineStatus


# ---------------------------------------------------------------------------
# /api/analytics/inventory-trend
# ---------------------------------------------------------------------------

class InventoryTrendPoint(BaseModel):
    date: date
    inventory_on_hand: Optional[float]
    forecasted_demand: Optional[float]
    reorder_point: Optional[float]
    safety_stock: Optional[float]


class InventoryTrendMetadata(BaseModel):
    product_id: Optional[str]
    store_id: Optional[str]
    days: int
    mode: str   # "aggregate" or "filtered"
    reorder_point_note: Optional[str]


class InventoryTrendResponse(BaseModel):
    series: list[InventoryTrendPoint]
    metadata: InventoryTrendMetadata


# ---------------------------------------------------------------------------
# /api/analytics/risk-drivers
# ---------------------------------------------------------------------------

class RiskDriver(BaseModel):
    name: str
    severity: str   # "high" / "medium" / "low"
    explanation: str


class RiskDriverEntry(BaseModel):
    product_id: str
    store_id: str
    product_name: Optional[str]
    sku: Optional[str]
    risk_tier: str
    risk_score: Optional[float]
    estimated_lost_sales: Optional[float]
    drivers: list[RiskDriver]


class RiskDriversResponse(BaseModel):
    drivers: list[RiskDriverEntry]
    total: int
    disclaimer: str


# ---------------------------------------------------------------------------
# /api/analytics/reorder-queue
# ---------------------------------------------------------------------------

class ReorderQueueItem(BaseModel):
    recommendation_id: str
    product_id: str
    store_id: str
    sku: Optional[str]
    product_name: Optional[str]
    category: Optional[str]
    risk_tier: Optional[str]
    recommended_units: Optional[float]
    estimated_order_cost: Optional[float]
    lead_time_days: Optional[int]
    urgency: str
    confidence_label: str   # "review_now" / "monitor" / "low_priority"
    reason: str
    status: str


class ReorderQueueResponse(BaseModel):
    items: list[ReorderQueueItem]
    total: int
    safety_note: str


# ---------------------------------------------------------------------------
# /api/analytics/executive-summary
# ---------------------------------------------------------------------------

class ExecutiveSummaryResponse(BaseModel):
    headline: str
    summary: list[str]
    next_actions: list[str]
    safety_note: str
