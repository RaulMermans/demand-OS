"""
API response schemas — shapes returned by FastAPI endpoints.
"""

from typing import Any, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class PipelineStatusResponse(BaseModel):
    status: str
    data_mode: str
    pipeline_ready: bool
    active_connector: str
    message: str


class OverviewResponse(BaseModel):
    status: str
    data_mode: str
    pipeline_ready: bool
    message: str
    summary: dict[str, Any]


class IngestionRunSummary(BaseModel):
    run_id: str
    connector: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    records_ingested: int
    counts: dict[str, Any]


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


class ScaffoldNotReady(BaseModel):
    status: str = "scaffold_ready"
    data_mode: str = "not_seeded"
    pipeline_ready: bool = False
    message: str = "This endpoint will be populated in Sprint 2 after data is seeded and the pipeline runs."
    endpoint: Optional[str] = None
