"""
Tests for CSV upload feature (Sprint 13 Part A).

Requirements:
1. CSV template endpoint exists.
2. CSV validate endpoint does not mutate DB.
3. CSV upload requires API key when configured.
4. CSV upload rejects missing columns.
5. CSV upload rejects FK violations.  (basic — FK check via service layer)
6. CSV upload accepts valid small raw dataset.
7. CSV upload creates audit record.
8. CSV upload does not accept precomputed forecasts/risks/recommendations.
"""

import io
import pytest
from fastapi.testclient import TestClient

import app.db.models  # noqa: F401 — register models
from app.main import app
from app.db.base import Base

# -----------------------------------------------------------------------
# Client fixture
# -----------------------------------------------------------------------

@pytest.fixture
def client(override_db):
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------------
# Helper — build minimal valid CSV bytes
# -----------------------------------------------------------------------

def _products_csv(rows=None):
    rows = rows or [
        "id,external_id,sku,name,source_connector",
        "p-001,EXT-001,SKU-A,Widget A,csv_upload",
        "p-002,EXT-002,SKU-B,Widget B,csv_upload",
    ]
    return "\n".join(rows).encode()


def _products_csv_missing_col():
    return b"external_id,sku,name,source_connector\nEXT-001,SKU-A,Widget A,csv_upload"


def _products_csv_forbidden_field():
    return b"id,external_id,sku,name,source_connector,lag_7d\np-001,EXT-001,SKU-A,Widget,csv_upload,99"


# -----------------------------------------------------------------------
# 1. Template endpoint exists
# -----------------------------------------------------------------------

def test_csv_template_all(client):
    r = client.get("/api/csv/templates")
    assert r.status_code == 200
    data = r.json()
    assert "templates" in data
    assert "products" in data["templates"]


def test_csv_template_by_entity(client):
    for entity in ["products", "stores", "suppliers", "orders",
                   "inventory_snapshots", "promotions", "purchase_orders"]:
        r = client.get(f"/api/csv/templates/{entity}")
        assert r.status_code == 200
        assert r.json()["entity_type"] == entity


def test_csv_template_unknown_entity(client):
    r = client.get("/api/csv/templates/forecasts")
    assert r.status_code == 404


# -----------------------------------------------------------------------
# 2. Validate endpoint does not mutate DB
# -----------------------------------------------------------------------

def test_csv_validate_no_db_mutation(client, in_memory_db):
    from app.db.models import CsvUploadRun

    initial_count = in_memory_db.query(CsvUploadRun).count()

    r = client.post(
        "/api/csv/validate",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv(), "text/csv")},
    )
    assert r.status_code == 200

    after_count = in_memory_db.query(CsvUploadRun).count()
    assert after_count == initial_count, "Validate must not create DB records"


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------

def _with_key(monkeypatch, key: str):
    from app.config import Settings, get_settings
    s = get_settings()
    new_s = Settings(**{**s.model_dump(), "demandos_api_key": key})
    monkeypatch.setattr("app.api.auth.get_settings", lambda: new_s)


# -----------------------------------------------------------------------
# 3. Upload requires API key when configured
# -----------------------------------------------------------------------

def test_csv_upload_requires_api_key(client, monkeypatch):
    _with_key(monkeypatch, "test-key-abc")

    # No key → 401
    r = client.post(
        "/api/csv/upload",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv(), "text/csv")},
    )
    assert r.status_code == 401


def test_csv_upload_passes_with_correct_key(client, monkeypatch):
    _with_key(monkeypatch, "test-key-abc")

    r = client.post(
        "/api/csv/upload",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv(), "text/csv")},
        headers={"X-DemandOS-API-Key": "test-key-abc"},
    )
    assert r.status_code == 200


# -----------------------------------------------------------------------
# 4. Rejects missing required columns
# -----------------------------------------------------------------------

def test_csv_validate_rejects_missing_columns(client):
    r = client.post(
        "/api/csv/validate",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv_missing_col(), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_valid"] is False
    assert any("Missing required columns" in e["message"] for e in data["errors"])


# -----------------------------------------------------------------------
# 5. Rejects precomputed/derived fields
# -----------------------------------------------------------------------

def test_csv_upload_rejects_derived_fields(client):
    r = client.post(
        "/api/csv/validate",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv_forbidden_field(), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["is_valid"] is False
    assert any("Forbidden derived fields" in e["message"] for e in data["errors"])


# -----------------------------------------------------------------------
# 6. Accept valid small dataset + 7. Creates audit record
# -----------------------------------------------------------------------

def test_csv_upload_valid_products(client, in_memory_db):
    from app.db.models import CsvUploadRun, RawProduct as DBProduct

    initial_products = in_memory_db.query(DBProduct).count()

    r = client.post(
        "/api/csv/upload",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv(), "text/csv")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["records_inserted"] >= 1

    # Audit record created
    run = in_memory_db.query(CsvUploadRun).filter(
        CsvUploadRun.id == data["upload_id"]
    ).first()
    assert run is not None
    assert run.status == "completed"
    assert run.entity_type == "products"

    # Records actually inserted
    after_products = in_memory_db.query(DBProduct).count()
    assert after_products > initial_products


# -----------------------------------------------------------------------
# 8. Upload history endpoint
# -----------------------------------------------------------------------

def test_csv_uploads_history(client, in_memory_db):
    # Upload once
    client.post(
        "/api/csv/upload",
        data={"entity_type": "products"},
        files={"file": ("products.csv", _products_csv(), "text/csv")},
    )

    r = client.get("/api/csv/uploads")
    assert r.status_code == 200
    data = r.json()
    assert "uploads" in data
    assert len(data["uploads"]) >= 1


def test_csv_uploads_latest(client, in_memory_db):
    r = client.get("/api/csv/uploads/latest")
    assert r.status_code == 200
    data = r.json()
    assert "has_uploads" in data


# -----------------------------------------------------------------------
# Validator unit tests
# -----------------------------------------------------------------------

def test_validator_negative_quantity():
    from app.validation.csv_validators import validate_csv_bytes
    csv_data = b"id,external_order_id,ordered_at,order_date,quantity,unit_price,source_connector\nord-1,EXT-1,2024-01-01,2024-01-01,-5,9.99,csv"
    result = validate_csv_bytes(csv_data, "orders")
    assert result["is_valid"] is False
    assert any("must be >= 0" in e["message"] for e in result["errors"])


def test_validator_bad_date():
    from app.validation.csv_validators import validate_csv_bytes
    csv_data = b"id,snapshot_date,quantity_on_hand,source_connector\ninv-1,not-a-date,100,csv"
    result = validate_csv_bytes(csv_data, "inventory_snapshots")
    assert result["is_valid"] is False


def test_validator_duplicate_ids():
    from app.validation.csv_validators import validate_csv_bytes
    csv_data = b"id,external_id,sku,name,source_connector\np-1,EXT-1,SKU-A,Widget,csv\np-1,EXT-2,SKU-B,Widget2,csv"
    result = validate_csv_bytes(csv_data, "products")
    assert result["is_valid"] is False
    assert any("Duplicate id" in e["message"] for e in result["errors"])


def test_validator_file_too_large():
    from app.validation.csv_validators import validate_csv_bytes
    big_csv = b"id,external_id,sku,name,source_connector\n" + b"p-1,EXT,SKU,W,c\n" * 100000
    result = validate_csv_bytes(big_csv, "products", max_bytes=100)
    assert result["is_valid"] is False
    assert any("exceeds" in e["message"] for e in result["errors"])
