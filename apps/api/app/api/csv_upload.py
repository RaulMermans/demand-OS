"""
CSV upload API — raw entity ingestion via file upload.

Endpoints:
  POST /api/csv/validate       — validate only, no DB mutation
  POST /api/csv/upload         — validate + ingest (API key required)
  GET  /api/csv/templates      — download/describe templates
  GET  /api/csv/templates/{entity_type}
  GET  /api/csv/uploads        — upload history
  GET  /api/csv/uploads/latest — latest upload run
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.db.session import get_db
from app.db.models import CsvUploadRun
from app.schemas.csv_upload import (
    CsvValidateResponse,
    CsvUploadResponse,
    CsvUploadRunSummary,
    CsvTemplate,
    CsvTemplateField,
    SUPPORTED_ENTITY_TYPES,
    MAX_CSV_BYTES,
)
from app.services.csv_ingestion_service import CsvIngestionService
from app.validation.csv_validators import validate_csv_bytes, ENTITY_SCHEMAS

router = APIRouter()


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, CsvTemplate] = {
    "products": CsvTemplate(
        entity_type="products",
        required_columns=["id", "external_id", "sku", "name", "source_connector"],
        optional_columns=["category", "brand", "supplier_id", "unit_cost", "unit_price",
                          "lead_time_days", "is_active"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique product ID", example="prod-001"),
            CsvTemplateField(name="external_id", required=True, type="string",
                             description="ID in source system", example="EXT-001"),
            CsvTemplateField(name="sku", required=True, type="string",
                             description="Stock keeping unit", example="SKU-WIDGET-A"),
            CsvTemplateField(name="name", required=True, type="string",
                             description="Product name", example="Blue Widget"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
            CsvTemplateField(name="category", required=False, type="string",
                             description="Product category", example="Widgets"),
            CsvTemplateField(name="unit_cost", required=False, type="float",
                             description="Cost per unit", example="4.99"),
            CsvTemplateField(name="unit_price", required=False, type="float",
                             description="Selling price per unit", example="9.99"),
            CsvTemplateField(name="lead_time_days", required=False, type="integer",
                             description="Supplier lead time in days", example="14"),
        ],
        example_rows=[
            {"id": "prod-001", "external_id": "EXT-001", "sku": "SKU-A",
             "name": "Blue Widget", "source_connector": "csv_upload",
             "category": "Widgets", "unit_cost": "4.99", "unit_price": "9.99",
             "lead_time_days": "14"},
        ],
        validation_notes=[
            "id must be unique across all rows",
            "unit_cost and unit_price must be >= 0",
            "lead_time_days must be a non-negative integer",
            "Derived fields (lag_7d, forecast, risk_score, etc.) are not accepted",
        ],
    ),
    "stores": CsvTemplate(
        entity_type="stores",
        required_columns=["id", "external_id", "name", "source_connector"],
        optional_columns=["region", "country", "timezone", "channel", "is_active"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique store ID", example="store-001"),
            CsvTemplateField(name="external_id", required=True, type="string",
                             description="ID in source system", example="SHP-001"),
            CsvTemplateField(name="name", required=True, type="string",
                             description="Store name", example="London Flagship"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
            CsvTemplateField(name="region", required=False, type="string",
                             description="Geographic region", example="EMEA"),
            CsvTemplateField(name="channel", required=False, type="string",
                             description="Sales channel (online/retail/wholesale)", example="retail"),
        ],
        example_rows=[
            {"id": "store-001", "external_id": "SHP-001", "name": "London Flagship",
             "source_connector": "csv_upload", "region": "EMEA", "channel": "retail"},
        ],
        validation_notes=[
            "id must be unique across all rows",
        ],
    ),
    "suppliers": CsvTemplate(
        entity_type="suppliers",
        required_columns=["id", "external_id", "name", "source_connector"],
        optional_columns=["country", "lead_time_days_min", "lead_time_days_max",
                          "reliability_score", "contact_email"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique supplier ID", example="sup-001"),
            CsvTemplateField(name="external_id", required=True, type="string",
                             description="ID in source system", example="SUP-EXT-001"),
            CsvTemplateField(name="name", required=True, type="string",
                             description="Supplier name", example="ACME Supply Co"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
            CsvTemplateField(name="reliability_score", required=False, type="float",
                             description="Raw reliability score from ERP (0–1)", example="0.92"),
        ],
        example_rows=[
            {"id": "sup-001", "external_id": "SUP-EXT-001", "name": "ACME Supply Co",
             "source_connector": "csv_upload", "lead_time_days_min": "7",
             "lead_time_days_max": "14", "reliability_score": "0.92"},
        ],
        validation_notes=[
            "reliability_score is the raw ERP score (0–1), not a computed metric",
            "lead_time_days_min and lead_time_days_max must be >= 0",
        ],
    ),
    "orders": CsvTemplate(
        entity_type="orders",
        required_columns=["id", "external_order_id", "ordered_at", "order_date",
                          "quantity", "unit_price", "source_connector"],
        optional_columns=["store_id", "product_id", "discount_amount",
                          "currency", "status", "promotion_id"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique order line ID", example="ord-001-line-1"),
            CsvTemplateField(name="external_order_id", required=True, type="string",
                             description="Order ID in source system", example="ORD-20240101-001"),
            CsvTemplateField(name="ordered_at", required=True, type="datetime",
                             description="Order timestamp (ISO 8601)", example="2024-01-15T10:30:00"),
            CsvTemplateField(name="order_date", required=True, type="date",
                             description="Order date (YYYY-MM-DD)", example="2024-01-15"),
            CsvTemplateField(name="quantity", required=True, type="float",
                             description="Units ordered", example="5"),
            CsvTemplateField(name="unit_price", required=True, type="float",
                             description="Price per unit at order time", example="9.99"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
        ],
        example_rows=[
            {"id": "ord-001-line-1", "external_order_id": "ORD-001",
             "store_id": "store-001", "product_id": "prod-001",
             "ordered_at": "2024-01-15T10:30:00", "order_date": "2024-01-15",
             "quantity": "5", "unit_price": "9.99", "source_connector": "csv_upload"},
        ],
        validation_notes=[
            "quantity and unit_price must be >= 0",
            "ordered_at must be a valid ISO 8601 datetime",
            "order_date must be YYYY-MM-DD",
        ],
    ),
    "inventory_snapshots": CsvTemplate(
        entity_type="inventory_snapshots",
        required_columns=["id", "snapshot_date", "quantity_on_hand", "source_connector"],
        optional_columns=["store_id", "product_id", "quantity_on_order",
                          "quantity_reserved", "warehouse_location"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique snapshot ID", example="inv-001"),
            CsvTemplateField(name="snapshot_date", required=True, type="date",
                             description="Date of snapshot (YYYY-MM-DD)", example="2024-01-15"),
            CsvTemplateField(name="quantity_on_hand", required=True, type="float",
                             description="Units on hand at snapshot time", example="120"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
        ],
        example_rows=[
            {"id": "inv-001", "store_id": "store-001", "product_id": "prod-001",
             "snapshot_date": "2024-01-15", "quantity_on_hand": "120",
             "quantity_on_order": "50", "source_connector": "csv_upload"},
        ],
        validation_notes=[
            "quantity_on_hand, quantity_on_order, quantity_reserved must be >= 0",
        ],
    ),
    "promotions": CsvTemplate(
        entity_type="promotions",
        required_columns=["id", "external_id", "source_connector"],
        optional_columns=["name", "promotion_type", "discount_pct", "start_date",
                          "end_date", "applicable_skus", "applicable_stores"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique promotion ID", example="promo-001"),
            CsvTemplateField(name="external_id", required=True, type="string",
                             description="ID in source system", example="PROMO-EXT-001"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
            CsvTemplateField(name="discount_pct", required=False, type="float",
                             description="Discount percentage (0–100)", example="15.0"),
        ],
        example_rows=[
            {"id": "promo-001", "external_id": "PROMO-EXT-001",
             "name": "January Sale", "promotion_type": "discount",
             "discount_pct": "15.0", "start_date": "2024-01-01",
             "end_date": "2024-01-31", "source_connector": "csv_upload"},
        ],
        validation_notes=[
            "discount_pct must be >= 0",
            "start_date and end_date must be YYYY-MM-DD if provided",
        ],
    ),
    "purchase_orders": CsvTemplate(
        entity_type="purchase_orders",
        required_columns=["id", "external_po_id", "ordered_at", "quantity_ordered",
                          "source_connector"],
        optional_columns=["supplier_id", "product_id", "store_id",
                          "expected_delivery_date", "unit_cost", "status"],
        fields=[
            CsvTemplateField(name="id", required=True, type="string",
                             description="Unique PO ID", example="po-001"),
            CsvTemplateField(name="external_po_id", required=True, type="string",
                             description="PO ID in source system", example="PO-EXT-001"),
            CsvTemplateField(name="ordered_at", required=True, type="datetime",
                             description="PO creation timestamp", example="2024-01-10T09:00:00"),
            CsvTemplateField(name="quantity_ordered", required=True, type="float",
                             description="Units ordered", example="200"),
            CsvTemplateField(name="source_connector", required=True, type="string",
                             description="Data source identifier", example="csv_upload"),
        ],
        example_rows=[
            {"id": "po-001", "external_po_id": "PO-EXT-001",
             "supplier_id": "sup-001", "product_id": "prod-001",
             "ordered_at": "2024-01-10T09:00:00", "quantity_ordered": "200",
             "expected_delivery_date": "2024-01-24", "unit_cost": "4.99",
             "status": "confirmed", "source_connector": "csv_upload"},
        ],
        validation_notes=[
            "quantity_ordered must be >= 0",
            "This is a historical purchase order record, not a new order creation",
        ],
    ),
}


@router.get("/csv/templates")
def get_all_templates() -> dict:
    return {
        "entity_types": SUPPORTED_ENTITY_TYPES,
        "templates": {k: v.model_dump() for k, v in TEMPLATES.items()},
        "note": "CSV mode imports raw operational data only. Derived fields are not accepted.",
        "max_file_size_bytes": MAX_CSV_BYTES,
    }


@router.get("/csv/templates/{entity_type}")
def get_template(entity_type: str) -> dict:
    if entity_type not in TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"No template for entity type '{entity_type}'. "
                   f"Supported: {SUPPORTED_ENTITY_TYPES}",
        )
    return TEMPLATES[entity_type].model_dump()


@router.post("/csv/validate")
async def validate_csv(
    entity_type: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    """Validate a CSV file without mutating the database."""
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported entity type '{entity_type}'. "
                   f"Supported: {SUPPORTED_ENTITY_TYPES}",
        )

    raw_bytes = await file.read()

    result = validate_csv_bytes(raw_bytes, entity_type)

    return {
        "entity_type": entity_type,
        "filename": file.filename or "unknown",
        "row_count": result["row_count"],
        "valid_row_count": result["valid_row_count"],
        "invalid_row_count": result["invalid_row_count"],
        "errors": result["errors"],
        "warnings": result["warnings"],
        "is_valid": result["is_valid"],
    }


@router.post("/csv/upload")
async def upload_csv(
    entity_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> dict:
    """Validate and ingest a CSV file. Requires API key when configured."""
    if entity_type not in SUPPORTED_ENTITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported entity type '{entity_type}'. "
                   f"Supported: {SUPPORTED_ENTITY_TYPES}",
        )

    raw_bytes = await file.read()
    filename = file.filename or "unknown.csv"

    service = CsvIngestionService(db)
    result = service.ingest(raw_bytes, entity_type, filename, dry_run=False)

    if result["status"] == "failed":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "CSV validation failed",
                "errors": result["error_summary"],
                "row_count": result["row_count"],
                "valid_row_count": result["valid_row_count"],
                "invalid_row_count": result["invalid_row_count"],
            },
        )

    return result


@router.get("/csv/uploads")
def get_uploads(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    runs = (
        db.query(CsvUploadRun)
        .order_by(CsvUploadRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "uploads": [
            {
                "upload_id": r.id,
                "entity_type": r.entity_type,
                "filename": r.filename,
                "status": r.status,
                "row_count": r.row_count,
                "valid_row_count": r.valid_row_count,
                "invalid_row_count": r.invalid_row_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }


@router.get("/csv/uploads/latest")
def get_latest_upload(db: Session = Depends(get_db)) -> dict:
    run = (
        db.query(CsvUploadRun)
        .order_by(CsvUploadRun.created_at.desc())
        .first()
    )
    if not run:
        return {"upload": None, "has_uploads": False}
    return {
        "upload": {
            "upload_id": run.id,
            "entity_type": run.entity_type,
            "filename": run.filename,
            "status": run.status,
            "row_count": run.row_count,
            "valid_row_count": run.valid_row_count,
            "invalid_row_count": run.invalid_row_count,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        },
        "has_uploads": True,
    }
