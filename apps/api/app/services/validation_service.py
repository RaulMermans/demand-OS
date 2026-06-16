"""
ValidationService — validates raw records before persistence.

Sprint 1 TODO: Implement checks:
  - Required fields present and correctly typed
  - Date ranges are plausible (not future-dated, not ancient)
  - Quantities and prices are non-negative
  - External IDs are non-empty strings
  - Referential integrity hints (product_id exists in raw_products)
  - Duplicate detection by (external_id, connector)
  - Field guard: raw records must not contain derived/ML fields
"""

from typing import Any


class ValidationService:
    def validate_raw_records(self, records: list[Any]) -> dict:
        """
        Scaffold: no validation logic yet.
        Sprint 1 TODO: implement per-schema validation rules.
        """
        return {
            "status": "scaffold_ready",
            "message": "ValidationService not yet implemented — Sprint 1.",
            "records_checked": len(records),
            "errors": [],
            "warnings": [],
        }
