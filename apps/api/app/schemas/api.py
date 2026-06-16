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


class DataHealthResponse(BaseModel):
    status: str
    data_mode: str
    checks: list[dict[str, Any]]
    message: str


class ScaffoldNotReady(BaseModel):
    status: str = "scaffold_ready"
    data_mode: str = "not_seeded"
    pipeline_ready: bool = False
    message: str = "This endpoint will be populated in Sprint 2 after data is seeded and the pipeline runs."
    endpoint: Optional[str] = None
