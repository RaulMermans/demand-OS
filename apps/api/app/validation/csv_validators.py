"""
CSV validators for raw entity uploads.

Rules:
- Required columns must be present.
- Forbidden derived fields are rejected.
- Dates must be parseable ISO format.
- Negative quantities are rejected for inventory/order fields.
- No FK violation checks at validate-only time; those run at upload time.
"""

import csv
import io
from datetime import date, datetime
from typing import Any

from app.schemas.raw import FORBIDDEN_DERIVED_FIELDS

# ---------------------------------------------------------------------------
# Per-entity column definitions
# ---------------------------------------------------------------------------

ENTITY_SCHEMAS: dict[str, dict] = {
    "products": {
        "required": ["id", "external_id", "sku", "name", "source_connector"],
        "optional": ["category", "brand", "supplier_id", "unit_cost", "unit_price",
                     "lead_time_days", "is_active"],
        "non_negative": ["unit_cost", "unit_price", "lead_time_days"],
        "date_fields": [],
    },
    "stores": {
        "required": ["id", "external_id", "name", "source_connector"],
        "optional": ["region", "country", "timezone", "channel", "is_active"],
        "non_negative": [],
        "date_fields": [],
    },
    "suppliers": {
        "required": ["id", "external_id", "name", "source_connector"],
        "optional": ["country", "lead_time_days_min", "lead_time_days_max",
                     "reliability_score", "contact_email"],
        "non_negative": ["lead_time_days_min", "lead_time_days_max"],
        "date_fields": [],
    },
    "orders": {
        "required": ["id", "external_order_id", "ordered_at", "order_date",
                     "quantity", "unit_price", "source_connector"],
        "optional": ["store_id", "product_id", "discount_amount", "currency",
                     "status", "promotion_id"],
        "non_negative": ["quantity", "unit_price", "discount_amount"],
        "date_fields": ["order_date", "ordered_at"],
    },
    "inventory_snapshots": {
        "required": ["id", "snapshot_date", "quantity_on_hand", "source_connector"],
        "optional": ["store_id", "product_id", "quantity_on_order",
                     "quantity_reserved", "warehouse_location"],
        "non_negative": ["quantity_on_hand", "quantity_on_order", "quantity_reserved"],
        "date_fields": ["snapshot_date"],
    },
    "promotions": {
        "required": ["id", "external_id", "source_connector"],
        "optional": ["name", "promotion_type", "discount_pct", "start_date",
                     "end_date", "applicable_skus", "applicable_stores"],
        "non_negative": ["discount_pct"],
        "date_fields": ["start_date", "end_date"],
    },
    "purchase_orders": {
        "required": ["id", "external_po_id", "ordered_at", "quantity_ordered",
                     "source_connector"],
        "optional": ["supplier_id", "product_id", "store_id",
                     "expected_delivery_date", "unit_cost", "status"],
        "non_negative": ["quantity_ordered", "unit_cost"],
        "date_fields": ["ordered_at", "expected_delivery_date"],
    },
}


def _parse_date(value: str) -> bool:
    """Return True if value is a parseable date/datetime string."""
    if not value:
        return True  # optional empty is fine
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S"):
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            pass
    return False


def validate_csv_bytes(
    raw_bytes: bytes,
    entity_type: str,
    max_bytes: int = 2 * 1024 * 1024,
) -> dict[str, Any]:
    """
    Validate raw CSV bytes for an entity type.

    Returns a dict with:
        row_count, valid_row_count, invalid_row_count, errors, warnings, is_valid
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    if len(raw_bytes) > max_bytes:
        return {
            "row_count": 0,
            "valid_row_count": 0,
            "invalid_row_count": 0,
            "errors": [{"row": 0, "field": "_file", "message": f"File exceeds {max_bytes // 1024}KB limit"}],
            "warnings": [],
            "is_valid": False,
        }

    if entity_type not in ENTITY_SCHEMAS:
        return {
            "row_count": 0,
            "valid_row_count": 0,
            "invalid_row_count": 0,
            "errors": [{"row": 0, "field": "_entity_type",
                        "message": f"Unsupported entity type: {entity_type}"}],
            "warnings": [],
            "is_valid": False,
        }

    schema = ENTITY_SCHEMAS[entity_type]
    required = set(schema["required"])
    all_known = set(schema["required"]) | set(schema["optional"])
    non_negative = set(schema["non_negative"])
    date_fields = set(schema["date_fields"])

    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return {
            "row_count": 0,
            "valid_row_count": 0,
            "invalid_row_count": 0,
            "errors": [{"row": 0, "field": "_header", "message": "Empty or unparseable CSV"}],
            "warnings": [],
            "is_valid": False,
        }

    headers = set(reader.fieldnames)

    # Reject forbidden derived fields
    forbidden_found = headers & FORBIDDEN_DERIVED_FIELDS
    if forbidden_found:
        return {
            "row_count": 0,
            "valid_row_count": 0,
            "invalid_row_count": 0,
            "errors": [{"row": 0, "field": "_header",
                        "message": f"Forbidden derived fields detected: {sorted(forbidden_found)}. "
                                   "DemandOS accepts raw operational data only."}],
            "warnings": [],
            "is_valid": False,
        }

    # Missing required columns
    missing = required - headers
    if missing:
        return {
            "row_count": 0,
            "valid_row_count": 0,
            "invalid_row_count": 0,
            "errors": [{"row": 0, "field": "_header",
                        "message": f"Missing required columns: {sorted(missing)}"}],
            "warnings": [],
            "is_valid": False,
        }

    # Unknown columns → warn only
    unknown = headers - all_known - {"id"}  # id always allowed
    if unknown:
        warnings.append({"row": 0, "field": "_header",
                         "message": f"Unknown columns (will be ignored): {sorted(unknown)}"})

    seen_ids: set[str] = set()
    row_count = 0
    valid_count = 0
    invalid_rows: set[int] = set()

    for row_num, row in enumerate(reader, start=2):
        row_count += 1
        row_errors = False

        # Required fields non-empty
        for col in required:
            val = (row.get(col) or "").strip()
            if not val:
                errors.append({"row": row_num, "field": col,
                                "message": f"Required field '{col}' is empty"})
                row_errors = True

        # Duplicate ID check
        row_id = (row.get("id") or "").strip()
        if row_id:
            if row_id in seen_ids:
                errors.append({"row": row_num, "field": "id",
                                "message": f"Duplicate id '{row_id}'"})
                row_errors = True
            seen_ids.add(row_id)

        # Non-negative numeric fields
        for col in non_negative:
            val = (row.get(col) or "").strip()
            if val:
                try:
                    num = float(val)
                    if num < 0:
                        errors.append({"row": row_num, "field": col,
                                       "message": f"'{col}' must be >= 0, got {num}"})
                        row_errors = True
                except ValueError:
                    errors.append({"row": row_num, "field": col,
                                   "message": f"'{col}' is not a valid number: {val!r}"})
                    row_errors = True

        # Date field format
        for col in date_fields:
            val = (row.get(col) or "").strip()
            if val and not _parse_date(val):
                errors.append({"row": row_num, "field": col,
                               "message": f"'{col}' is not a valid date/datetime: {val!r}"})
                row_errors = True

        if not row_errors:
            valid_count += 1

    return {
        "row_count": row_count,
        "valid_row_count": valid_count,
        "invalid_row_count": row_count - valid_count,
        "errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0 and row_count > 0,
    }
