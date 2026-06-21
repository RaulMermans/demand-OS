"""
CSV upload schemas — request/response shapes for the CSV ingestion feature.

Only raw operational entity types are accepted.
Precomputed derived fields are rejected by the validator.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


SUPPORTED_ENTITY_TYPES = [
    "products",
    "stores",
    "suppliers",
    "orders",
    "inventory_snapshots",
    "promotions",
    "purchase_orders",
]

MAX_CSV_BYTES = 2 * 1024 * 1024  # 2 MB


class CsvValidateResponse(BaseModel):
    entity_type: str
    filename: str
    row_count: int
    valid_row_count: int
    invalid_row_count: int
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    is_valid: bool


class CsvUploadResponse(BaseModel):
    upload_id: str
    entity_type: str
    filename: str
    status: str
    row_count: int
    valid_row_count: int
    invalid_row_count: int
    records_inserted: int
    error_summary: list[dict[str, Any]]
    created_at: datetime
    completed_at: Optional[datetime] = None


class CsvUploadRunSummary(BaseModel):
    upload_id: str
    entity_type: str
    filename: str
    status: str
    row_count: int
    valid_row_count: int
    invalid_row_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None


class CsvTemplateField(BaseModel):
    name: str
    required: bool
    type: str
    description: str
    example: str


class CsvTemplate(BaseModel):
    entity_type: str
    required_columns: list[str]
    optional_columns: list[str]
    fields: list[CsvTemplateField]
    example_rows: list[dict[str, Any]]
    validation_notes: list[str]
