"""
Sprint 9 — API key guard tests.

Tests:
1. Guard disabled when DEMANDOS_API_KEY is not configured — requests pass.
2. Guard blocks requests with missing key when key is configured.
3. Guard blocks requests with wrong key when key is configured.
4. Guard accepts correct key.
5. Read-only endpoints remain accessible without a key.
6. No key value is returned or logged in error responses.
7. Pipeline-status endpoint returns honest state.
8. Product drilldown endpoint returns 404 for unknown product.
9. Product drilldown returns product data when seeded.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(override_db):
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helper — guard bypassed by monkeypatching config
# ---------------------------------------------------------------------------

def _with_key(monkeypatch, key: str):
    """Patch settings to enable the API key guard with the given key."""
    from app.config import get_settings, Settings

    original_settings = get_settings()
    new_settings = Settings(
        **{
            **original_settings.model_dump(),
            "demandos_api_key": key,
        }
    )
    monkeypatch.setattr("app.api.auth.get_settings", lambda: new_settings)


# ---------------------------------------------------------------------------
# 1. Guard disabled when no key configured
# ---------------------------------------------------------------------------

def test_guard_disabled_allows_demo_reset(client):
    """POST /api/demo/reset succeeds when no API key is configured."""
    resp = client.post("/api/demo/reset")
    assert resp.status_code != 401
    assert resp.status_code != 403


def test_guard_disabled_allows_aggregation_run(client):
    resp = client.post("/api/aggregation/run", json={})
    assert resp.status_code != 401


def test_guard_disabled_allows_features_build(client):
    resp = client.post("/api/features/build", json={})
    assert resp.status_code != 401


def test_guard_disabled_allows_risks_run(client):
    resp = client.post("/api/risks/run", json={})
    assert resp.status_code != 401


def test_guard_disabled_allows_recommendations_run(client):
    resp = client.post("/api/recommendations/run", json={})
    assert resp.status_code != 401


# ---------------------------------------------------------------------------
# 2. Guard blocks missing key when configured
# ---------------------------------------------------------------------------

def test_guard_blocks_missing_key(client, monkeypatch):
    _with_key(monkeypatch, "secret-test-key-abc")
    resp = client.post("/api/aggregation/run", json={})
    assert resp.status_code == 401
    detail = resp.json().get("detail", "")
    assert "API-Key" in detail or "key" in detail.lower()


def test_guard_blocks_missing_key_on_demo_reset(client, monkeypatch):
    _with_key(monkeypatch, "secret-test-key-abc")
    resp = client.post("/api/demo/reset", json={})
    assert resp.status_code == 401


def test_guard_blocks_missing_key_on_features(client, monkeypatch):
    _with_key(monkeypatch, "secret-test-key-abc")
    resp = client.post("/api/features/build", json={})
    assert resp.status_code == 401


def test_guard_blocks_missing_key_on_risks(client, monkeypatch):
    _with_key(monkeypatch, "secret-test-key-abc")
    resp = client.post("/api/risks/run", json={})
    assert resp.status_code == 401


def test_guard_blocks_missing_key_on_recommendations(client, monkeypatch):
    _with_key(monkeypatch, "secret-test-key-abc")
    resp = client.post("/api/recommendations/run", json={})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3. Guard blocks wrong key
# ---------------------------------------------------------------------------

def test_guard_blocks_wrong_key(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.post(
        "/api/aggregation/run",
        json={},
        headers={"X-DemandOS-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_guard_blocks_wrong_key_on_recommendations(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.post(
        "/api/recommendations/run",
        json={},
        headers={"X-DemandOS-API-Key": "not-the-right-key"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 4. Guard accepts correct key
# ---------------------------------------------------------------------------

def test_guard_accepts_correct_key_aggregation(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.post(
        "/api/aggregation/run",
        json={},
        headers={"X-DemandOS-API-Key": "correct-key-xyz"},
    )
    assert resp.status_code != 401
    assert resp.status_code != 403


def test_guard_accepts_correct_key_features(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.post(
        "/api/features/build",
        json={},
        headers={"X-DemandOS-API-Key": "correct-key-xyz"},
    )
    assert resp.status_code != 401


def test_guard_accepts_correct_key_recommendations(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.post(
        "/api/recommendations/run",
        json={},
        headers={"X-DemandOS-API-Key": "correct-key-xyz"},
    )
    assert resp.status_code != 401


# ---------------------------------------------------------------------------
# 5. Read-only endpoints remain accessible without key
# ---------------------------------------------------------------------------

def test_read_endpoint_accessible_without_key(client, monkeypatch):
    """GET endpoints should work even when API key guard is enabled."""
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.get("/api/overview")
    assert resp.status_code == 200


def test_read_risks_accessible_without_key(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.get("/api/risks")
    assert resp.status_code == 200


def test_read_recommendations_accessible_without_key(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200


def test_health_accessible_without_key(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.get("/health")
    assert resp.status_code == 200


def test_data_health_accessible_without_key(client, monkeypatch):
    _with_key(monkeypatch, "correct-key-xyz")
    resp = client.get("/api/data-health")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 6. Error response does not contain the key value
# ---------------------------------------------------------------------------

def test_error_response_does_not_leak_key(client, monkeypatch):
    secret = "super-secret-key-do-not-log"
    _with_key(monkeypatch, secret)
    resp = client.post(
        "/api/aggregation/run",
        json={},
        headers={"X-DemandOS-API-Key": "wrong"},
    )
    assert resp.status_code == 401
    body = resp.text
    assert secret not in body


# ---------------------------------------------------------------------------
# 7. Pipeline-status endpoint returns honest state
# ---------------------------------------------------------------------------

def test_pipeline_status_no_data(client):
    resp = client.get("/api/dashboard/pipeline-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "steps" in data
    assert isinstance(data["steps"], list)
    assert len(data["steps"]) == 8
    assert "all_steps_complete" in data


def test_pipeline_status_step_fields(client):
    resp = client.get("/api/dashboard/pipeline-status")
    data = resp.json()
    for step in data["steps"]:
        assert "step" in step
        assert "label" in step
        assert "endpoint" in step
        assert "status" in step


def test_pipeline_status_no_data_steps_not_run(client):
    resp = client.get("/api/dashboard/pipeline-status")
    data = resp.json()
    non_reset_steps = [s for s in data["steps"] if s["step"] != "reset_demo"]
    for step in non_reset_steps:
        assert step["status"] == "not_run"


# ---------------------------------------------------------------------------
# 8. Product drilldown — 404 for unknown product
# ---------------------------------------------------------------------------

def test_product_drilldown_404_unknown(client):
    resp = client.get("/api/dashboard/product/nonexistent-product-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 9. Product drilldown returns data when product exists
# ---------------------------------------------------------------------------

def test_product_drilldown_returns_product(client):
    from app.db.models import RawProduct
    from sqlalchemy.orm import sessionmaker
    from app.db import session as db_session

    Session = sessionmaker(bind=db_session.engine)
    sess = Session()
    try:
        prod = RawProduct(
            id="test-product-001",
            external_id="EXT-001",
            sku="SKU-001",
            name="Test Widget",
            category="Tops",
            brand="TestBrand",
            unit_cost=10.0,
            unit_price=25.0,
            lead_time_days=14,
            is_active=True,
            source_connector="test",
        )
        sess.add(prod)
        sess.commit()
    finally:
        sess.close()

    resp = client.get("/api/dashboard/product/test-product-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["product_id"] == "test-product-001"
    assert data["product"]["sku"] == "SKU-001"
    assert data["product"]["name"] == "Test Widget"
    assert isinstance(data["risk_rows"], list)
    assert isinstance(data["recommendation_rows"], list)
    assert isinstance(data["forecast_rows"], list)
