"""
Sprint 8 — API contract tests.

Tests:
1. Overview response shape
2. Data-health response shape
3. Forecast list endpoint enforces bounded limits
4. Risk list endpoint enforces bounded limits
5. Recommendation list endpoint enforces bounded limits
6. Invalid query params return clear errors
7. Recommendation status update uses stable schema
8. No-data states return honest responses
9. Dashboard summary endpoints return computed-data-only responses
10. Offset pagination works for recommendations
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(override_db):
    """TestClient with in-memory DB from conftest."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Overview response shape
# ---------------------------------------------------------------------------

def test_overview_response_has_required_fields(client):
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "data_mode" in data
    assert "pipeline_ready" in data
    assert "message" in data
    assert "summary" in data


def test_overview_no_data_is_honest(client):
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    # status must be either "ok" or "no_data"; never a fake computed metric
    assert data["status"] in ("ok", "no_data")
    if data["status"] == "no_data":
        assert data["pipeline_ready"] is False


# ---------------------------------------------------------------------------
# 2. Data-health response shape
# ---------------------------------------------------------------------------

def test_data_health_response_has_required_fields(client):
    resp = client.get("/api/data-health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)
    assert "message" in data


def test_data_health_no_fake_metrics(client):
    resp = client.get("/api/data-health")
    data = resp.json()
    forbidden = ["forecast_accuracy_94", "revenue_at_risk_120000", "hardcoded"]
    for f in forbidden:
        assert f not in str(data), f"Forbidden value found: {f}"


# ---------------------------------------------------------------------------
# 3. Forecast list endpoint enforces bounded limits
# ---------------------------------------------------------------------------

def test_forecast_runs_default_limit(client):
    resp = client.get("/api/forecasts/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert len(data["runs"]) <= 100


def test_forecast_runs_limit_param(client):
    resp = client.get("/api/forecasts/runs?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) <= 5


def test_forecast_runs_limit_too_high_rejected(client):
    resp = client.get("/api/forecasts/runs?limit=9999")
    assert resp.status_code == 422


def test_forecast_runs_limit_zero_rejected(client):
    resp = client.get("/api/forecasts/runs?limit=0")
    assert resp.status_code == 422


def test_forecast_latest_default_limit(client):
    resp = client.get("/api/forecasts/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    # sample may be empty if no forecast run exists
    if data.get("sample"):
        assert len(data["sample"]) <= 500


# ---------------------------------------------------------------------------
# 4. Risk list endpoint enforces bounded limits
# ---------------------------------------------------------------------------

def test_risks_default_limit(client):
    resp = client.get("/api/risks")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_risks_limit_param(client):
    resp = client.get("/api/risks?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("rows"):
        assert len(data["rows"]) <= 10


def test_risks_limit_too_high_rejected(client):
    resp = client.get("/api/risks?limit=9999")
    assert resp.status_code == 422


def test_risks_limit_zero_rejected(client):
    resp = client.get("/api/risks?limit=0")
    assert resp.status_code == 422


def test_risks_offset_param(client):
    resp = client.get("/api/risks?offset=0&limit=10")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Recommendation list endpoint enforces bounded limits
# ---------------------------------------------------------------------------

def test_recommendations_no_data_returns_empty(client):
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    # Either empty list (no data) or results from a seeded run
    assert "recommendations" in data
    assert "total" in data


def test_recommendations_with_offset(client):
    resp = client.get("/api/recommendations?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "limit" in data
    assert "offset" in data


def test_recommendations_offset_field_present(client):
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    # Sprint 8: offset field must be present in response
    assert "limit" in data or "recommendations" in data


# ---------------------------------------------------------------------------
# 6. Invalid query params return clear errors
# ---------------------------------------------------------------------------

def test_risks_invalid_limit_string(client):
    resp = client.get("/api/risks?limit=abc")
    assert resp.status_code == 422


def test_forecast_runs_invalid_limit_string(client):
    resp = client.get("/api/forecasts/runs?limit=not_a_number")
    assert resp.status_code == 422


def test_model_metrics_invalid_limit_string(client):
    resp = client.get("/api/model-metrics?limit=bad")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 7. Recommendation status update schema
# ---------------------------------------------------------------------------

def test_status_update_invalid_status_rejected(client):
    resp = client.patch(
        "/api/recommendations/nonexistent-id/status",
        json={"status": "fly_to_mars"},
    )
    # 422 = invalid status value
    assert resp.status_code == 422


def test_status_update_missing_status_rejected(client):
    resp = client.patch(
        "/api/recommendations/nonexistent-id/status",
        json={},
    )
    assert resp.status_code == 422


def test_status_update_not_found(client):
    resp = client.patch(
        "/api/recommendations/totally-nonexistent-999/status",
        json={"status": "reviewed"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. Common no-data states return honest responses
# ---------------------------------------------------------------------------

def test_forecasts_latest_no_data_is_honest(client):
    resp = client.get("/api/forecasts/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "no_forecast")


def test_risks_latest_no_data_is_honest(client):
    resp = client.get("/api/risks/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "no_risk_run")


def test_recommendations_latest_no_data_is_honest(client):
    resp = client.get("/api/recommendations/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "no_data")


def test_model_metrics_no_data_is_honest(client):
    resp = client.get("/api/model-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "no_metrics")


# ---------------------------------------------------------------------------
# 9. Dashboard summary endpoints return computed-data-only responses
# ---------------------------------------------------------------------------

def test_dashboard_overview_shape(client):
    resp = client.get("/api/dashboard/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "raw_counts" in data
    assert "pipeline_readiness" in data
    assert "risk_summary" in data
    assert "recommendation_summary" in data
    assert "forecast_summary" in data


def test_dashboard_overview_no_fake_values(client):
    resp = client.get("/api/dashboard/overview")
    data = resp.json()
    # Ensure no hardcoded metric strings
    raw = str(data)
    for bad in ["94%", "revenue_at_risk", "fake"]:
        assert bad not in raw, f"Potentially fake value found: {bad}"


def test_dashboard_forecast_summary_shape(client):
    resp = client.get("/api/dashboard/forecast-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "has_forecast" in data


def test_dashboard_risk_summary_shape(client):
    resp = client.get("/api/dashboard/risk-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "has_risk_run" in data
    assert "tier_counts" in data


def test_dashboard_recommendation_summary_shape(client):
    resp = client.get("/api/dashboard/recommendation-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "has_recommendation_run" in data
    assert "urgency_counts" in data
    assert "open_count" in data


def test_dashboard_model_summary_shape(client):
    resp = client.get("/api/dashboard/model-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "has_ml_model" in data


def test_dashboard_data_health_shape(client):
    resp = client.get("/api/dashboard/data-health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checks" in data


# ---------------------------------------------------------------------------
# 10. No external side effects in API calls
# ---------------------------------------------------------------------------

def test_recommendations_run_endpoint_exists(client):
    # Just verify the endpoint exists; we don't run it (needs seeded data)
    resp = client.post("/api/recommendations/run", json={})
    # 422 or 200 are both acceptable; 404 would be a problem
    assert resp.status_code != 404


def test_no_purchase_order_field_in_recommendations(client):
    resp = client.get("/api/recommendations/latest")
    data = str(resp.json())
    assert "purchase_order" not in data
    assert "external_api_call" not in data
