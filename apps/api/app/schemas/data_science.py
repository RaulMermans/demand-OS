"""
Pydantic schemas for the data science summary layer (Sprint 15).

These are read-only response schemas — never used as connector input.
All values are computed from existing pipeline tables.
"""

from typing import Any, Optional
from pydantic import BaseModel


class DataVolumeSchema(BaseModel):
    products: int
    stores: int
    orders: int
    inventory_snapshots: int
    feature_rows: int
    forecast_rows: int


class ModelStatusSchema(BaseModel):
    latest_model: Optional[str]
    latest_wape: Optional[float]
    interpretation: str


class DecisionStatusSchema(BaseModel):
    critical_risks: int
    high_risks: int
    open_recommendations: int
    estimated_lost_sales: Optional[float]
    estimated_order_cost: Optional[float]


class DataScienceSummaryResponse(BaseModel):
    status: str
    pipeline_story: list[str]
    data_volume: DataVolumeSchema
    model_status: ModelStatusSchema
    decision_status: DecisionStatusSchema


# ---------------------------------------------------------------------------
# Forecast diagnostics
# ---------------------------------------------------------------------------

class ModelDiagnosticSchema(BaseModel):
    model_name: str
    model_type: str
    mae: Optional[float]
    rmse: Optional[float]
    wape: Optional[float]
    bias: Optional[float]
    forecast_rows: int
    backtest_horizon_days: Optional[int]
    interpretation: str
    quality_label: str   # "strong" | "directional" | "weak" | "unknown"
    warning: Optional[str]


class ForecastDiagnosticsResponse(BaseModel):
    status: str
    has_model: bool
    message: Optional[str]
    baseline: Optional[ModelDiagnosticSchema]
    ml_model: Optional[ModelDiagnosticSchema]
    wape_interpretation_guide: dict[str, str]


# ---------------------------------------------------------------------------
# Model comparison
# ---------------------------------------------------------------------------

class ModelComparisonEntrySchema(BaseModel):
    model_name: str
    model_type: str
    wape: Optional[float]
    mae: Optional[float]
    rmse: Optional[float]
    bias: Optional[float]
    rank: int
    quality_label: str
    strengths: list[str]
    limitations: list[str]
    best_for: str


class ModelComparisonResponse(BaseModel):
    status: str
    has_comparison: bool
    message: Optional[str]
    models: list[ModelComparisonEntrySchema]


# ---------------------------------------------------------------------------
# Feature signals
# ---------------------------------------------------------------------------

class FeatureSignalGroupSchema(BaseModel):
    group: str
    available: bool
    example_features: list[str]
    interpretation: str


class FeatureSignalsResponse(BaseModel):
    status: str
    source: str   # "feature_columns" | "no_model"
    total_features: int
    signals: list[FeatureSignalGroupSchema]
    disclaimer: str


# ---------------------------------------------------------------------------
# Business impact
# ---------------------------------------------------------------------------

class TopRiskEntrySchema(BaseModel):
    product_id: str
    product_name: Optional[str]
    store_id: str
    risk_tier: str
    days_until_stockout: Optional[float]
    lost_sales_value_estimate: Optional[float]


class TopRecommendationEntrySchema(BaseModel):
    product_id: str
    product_name: Optional[str]
    store_id: str
    urgency: str
    recommended_units: Optional[float]
    estimated_order_cost: Optional[float]


class BusinessImpactResponse(BaseModel):
    status: str
    has_data: bool
    message: Optional[str]
    estimated_lost_sales: Optional[float]
    estimated_order_cost: Optional[float]
    risk_tier_distribution: dict[str, int]
    recommendation_urgency_distribution: dict[str, int]
    top_risks: list[TopRiskEntrySchema]
    top_recommendations: list[TopRecommendationEntrySchema]
    review_guidance: list[str]
    automation_note: str
