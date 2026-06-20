"""
API response schemas — shapes returned by FastAPI endpoints.

Sprint 8: Hardened to cover all response families with explicit typed fields.
"""

from typing import Any, Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class StatusResponse(BaseModel):
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    status: str
    data_mode: str
    pipeline_ready: bool
    active_connector: str
    message: str


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginatedResponse(BaseModel):
    total: int
    returned: int
    limit: int
    offset: int
    items: list[Any]


# ---------------------------------------------------------------------------
# Overview / Data Health
# ---------------------------------------------------------------------------

class OverviewResponse(BaseModel):
    status: str
    data_mode: str
    pipeline_ready: bool
    message: str
    summary: dict[str, Any]


class DataHealthResponse(BaseModel):
    status: str
    data_mode: str
    products_count: int = 0
    stores_count: int = 0
    orders_count: int = 0
    inventory_snapshots_count: int = 0
    promotions_count: int = 0
    suppliers_count: int = 0
    purchase_orders_count: int = 0
    latest_ingestion_run: Optional[dict[str, Any]] = None
    checks: list[dict[str, Any]]
    message: str


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class IngestionRunResponse(BaseModel):
    run_id: str
    connector: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    records_ingested: int
    counts: dict[str, Any]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

class AggregationRunResponse(BaseModel):
    run_id: str
    status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None
    counts: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Feature
# ---------------------------------------------------------------------------

class FeatureRunResponse(BaseModel):
    run_id: str
    status: str
    rows_created: int
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------

class ForecastRunResponse(BaseModel):
    run_id: str
    model_name: str
    model_type: str
    mode: str
    horizon_days: int
    status: str
    started_at: str
    completed_at: Optional[str] = None
    rows_created: int
    test_start_date: Optional[str] = None
    test_end_date: Optional[str] = None


class ForecastRowResponse(BaseModel):
    id: str
    forecast_run_id: Optional[str] = None
    forecast_date: Optional[str] = None
    product_id: str
    store_id: str
    horizon_day: int
    model_type: Optional[str] = None
    p50_units: Optional[float] = None
    p10_units: Optional[float] = None
    p90_units: Optional[float] = None
    actual_units: Optional[float] = None
    absolute_error: Optional[float] = None
    absolute_percentage_error: Optional[float] = None


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class ModelVersionResponse(BaseModel):
    model_version_id: str
    model_name: Optional[str] = None
    algorithm: Optional[str] = None
    model_type: Optional[str] = None
    status: Optional[str] = None
    trained_at: Optional[str] = None
    training_start_date: Optional[str] = None
    training_end_date: Optional[str] = None
    test_start_date: Optional[str] = None
    test_end_date: Optional[str] = None
    artifact_path: Optional[str] = None
    metrics_summary: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


class ModelMetricResponse(BaseModel):
    id: str
    run_id: Optional[str] = None
    model_type: str
    horizon_days: Optional[int] = None
    level: Optional[str] = None
    level_value: Optional[str] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    wape: Optional[float] = None
    smape: Optional[float] = None
    bias: Optional[float] = None
    rows_evaluated: int = 0


# ---------------------------------------------------------------------------
# Stockout Risk
# ---------------------------------------------------------------------------

class StockoutRiskRunResponse(BaseModel):
    run_id: str
    mode: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    as_of_date: Optional[str] = None
    risk_horizon_days: Optional[int] = None
    rows_created: int = 0
    risk_counts: dict[str, int]
    source_forecast_run_id: Optional[str] = None
    error_message: Optional[str] = None


class StockoutRiskResponse(BaseModel):
    id: str
    risk_run_id: str
    as_of_date: Optional[str] = None
    product_id: str
    store_id: str
    category: Optional[str] = None
    supplier_id: Optional[str] = None
    current_available_units: Optional[float] = None
    inbound_units_within_horizon: Optional[float] = None
    forecast_demand_p50: Optional[float] = None
    days_of_supply: Optional[float] = None
    days_until_stockout: Optional[float] = None
    expected_stockout_date: Optional[str] = None
    safety_stock_units: Optional[float] = None
    lost_sales_value_estimate: Optional[float] = None
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

class RecommendationRunResponse(BaseModel):
    run_id: str
    source_risk_run_id: Optional[str] = None
    mode: Optional[str] = None
    status: str
    as_of_date: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    rows_created: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    total_recommended_units: Optional[float] = None
    total_estimated_value: Optional[float] = None


class ReorderRecommendationResponse(BaseModel):
    id: str
    recommendation_run_id: str
    product_id: str
    store_id: str
    category: Optional[str] = None
    supplier_id: Optional[str] = None
    risk_tier: Optional[str] = None
    risk_score: Optional[float] = None
    days_until_stockout: Optional[float] = None
    current_available_units: Optional[float] = None
    inventory_position: Optional[float] = None
    recommended_units_rounded: Optional[float] = None
    estimated_order_cost: Optional[float] = None
    estimated_lost_sales_avoided: Optional[float] = None
    urgency: Optional[str] = None
    recommendation_reason: Optional[str] = None
    confidence_level: Optional[str] = None
    status: str


class RecommendationStatusUpdateResponse(BaseModel):
    status: str
    recommendation_id: str
    new_status: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    note: str


# ---------------------------------------------------------------------------
# Dashboard summaries
# ---------------------------------------------------------------------------

class DashboardOverviewResponse(BaseModel):
    status: str
    raw_counts: dict[str, int]
    pipeline_readiness: dict[str, Any]
    risk_summary: dict[str, Any]
    recommendation_summary: dict[str, Any]
    forecast_summary: dict[str, Any]


class DashboardForecastSummaryResponse(BaseModel):
    status: str
    has_forecast: bool
    latest_run: Optional[dict[str, Any]] = None
    metrics: Optional[dict[str, Any]] = None
    message: Optional[str] = None


class DashboardRiskSummaryResponse(BaseModel):
    status: str
    has_risk_run: bool
    latest_run: Optional[dict[str, Any]] = None
    tier_counts: dict[str, int]
    estimated_lost_sales_value: Optional[float] = None
    message: Optional[str] = None


class DashboardRecommendationSummaryResponse(BaseModel):
    status: str
    has_recommendation_run: bool
    latest_run: Optional[dict[str, Any]] = None
    urgency_counts: dict[str, int]
    open_count: int
    total_estimated_order_cost: Optional[float] = None
    message: Optional[str] = None


class DashboardModelSummaryResponse(BaseModel):
    status: str
    has_ml_model: bool
    latest_model_version: Optional[dict[str, Any]] = None
    baseline_comparison: Optional[dict[str, Any]] = None
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Scaffold / legacy
# ---------------------------------------------------------------------------

class ScaffoldNotReady(BaseModel):
    status: str = "scaffold_ready"
    data_mode: str = "not_seeded"
    pipeline_ready: bool = False
    message: str = "This endpoint will be populated after the pipeline runs."
    endpoint: Optional[str] = None


# ---------------------------------------------------------------------------
# Ingestion run summary (legacy alias)
# ---------------------------------------------------------------------------

IngestionRunSummary = IngestionRunResponse
AggregationRunSummary = AggregationRunResponse
