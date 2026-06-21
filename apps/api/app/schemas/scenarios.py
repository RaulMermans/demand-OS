"""
Scenario planning schemas.

Scenario runs simulate what-if changes against the current pipeline baseline.
They never mutate the canonical forecast/risk/recommendation tables.
All outputs are clearly labelled as simulated.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


ALLOWED_HORIZON_DAYS = {7, 14, 28, 56, 90}


class ScenarioInputs(BaseModel):
    demand_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    lead_time_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    supplier_reliability_delta: float = Field(default=0.0, ge=-0.3, le=0.3)
    promotion_lift_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    inventory_adjustment_units: float = Field(default=0.0, ge=-1000.0, le=1000.0)
    horizon_days: int = Field(default=28)

    @field_validator("horizon_days")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        if v not in ALLOWED_HORIZON_DAYS:
            raise ValueError(f"horizon_days must be one of {sorted(ALLOWED_HORIZON_DAYS)}")
        return v


class ScenarioSummary(BaseModel):
    total_product_stores: int
    high_risk_count: int
    critical_risk_count: int
    total_lost_sales_estimate: float
    total_order_cost_estimate: float


class ScenarioRunResponse(BaseModel):
    scenario_id: str
    status: str
    inputs: ScenarioInputs
    baseline_summary: ScenarioSummary
    scenario_summary: ScenarioSummary
    delta_lost_sales: float
    delta_order_cost: float
    delta_high_risk_count: int
    delta_critical_risk_count: int
    top_impacted_product_stores: list[dict[str, Any]]
    created_at: datetime
    simulated: bool = True


class ScenarioRunListItem(BaseModel):
    scenario_id: str
    status: str
    inputs: dict[str, Any]
    delta_high_risk_count: Optional[int] = None
    delta_critical_risk_count: Optional[int] = None
    delta_lost_sales: Optional[float] = None
    created_at: datetime
    simulated: bool = True
