"""
Test: raw Pydantic schemas must not contain precomputed ML/forecast/risk fields.

This enforces DemandOS's non-negotiable raw-data-only rule:
connectors return raw operational records only; the pipeline computes everything else.
"""

import pytest
from app.schemas.raw import ALL_RAW_SCHEMAS, FORBIDDEN_DERIVED_FIELDS


@pytest.mark.parametrize("schema_cls", ALL_RAW_SCHEMAS)
def test_raw_schema_has_no_derived_fields(schema_cls):
    """No raw schema may include ML feature, forecast, risk, or recommendation fields."""
    schema_fields = set(schema_cls.model_fields.keys())
    violations = schema_fields & FORBIDDEN_DERIVED_FIELDS
    assert not violations, (
        f"{schema_cls.__name__} contains forbidden derived fields: {violations}. "
        "Raw schemas must only contain operational data as received from the source system."
    )


def test_forbidden_fields_list_is_non_empty():
    """Guard: the forbidden field list itself must not be accidentally emptied."""
    assert len(FORBIDDEN_DERIVED_FIELDS) >= 10, (
        "FORBIDDEN_DERIVED_FIELDS should contain at least 10 derived field names."
    )


def test_all_raw_schemas_list_is_non_empty():
    """Guard: the schema list must contain all expected raw schemas."""
    assert len(ALL_RAW_SCHEMAS) >= 7, (
        "ALL_RAW_SCHEMAS should list all 7 raw operational schemas."
    )


def test_each_raw_schema_has_source_connector_field():
    """Every raw schema must carry a source_connector field for provenance tracking."""
    for schema_cls in ALL_RAW_SCHEMAS:
        assert "source_connector" in schema_cls.model_fields, (
            f"{schema_cls.__name__} is missing required 'source_connector' field."
        )


def test_each_raw_schema_has_id_field():
    """Every raw schema must have an id field."""
    for schema_cls in ALL_RAW_SCHEMAS:
        assert "id" in schema_cls.model_fields, (
            f"{schema_cls.__name__} is missing required 'id' field."
        )
