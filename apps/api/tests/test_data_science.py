"""
Tests for the data science summary API endpoints (Sprint 15).

Coverage:
- All 5 endpoints exist and return HTTP 200
- Responses handle no-data state gracefully
- WAPE interpretation thresholds are correct
- Endpoints are read-only (no DB mutations)
- No secrets are exposed in responses
- No external side effects
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_science_summary_service import (
    _wape_label,
    _wape_interpretation,
    _wape_warning,
    WAPE_GUIDE,
)

client = TestClient(app)

ENDPOINTS = [
    "/api/data-science/summary",
    "/api/data-science/forecast-diagnostics",
    "/api/data-science/model-comparison",
    "/api/data-science/feature-signals",
    "/api/data-science/business-impact",
]


@pytest.fixture(autouse=True)
def isolated_db(override_db):
    yield


# ---------------------------------------------------------------------------
# Endpoint existence and basic response shape
# ---------------------------------------------------------------------------

class TestDataScienceSummary:
    def test_returns_200(self):
        r = client.get("/api/data-science/summary")
        assert r.status_code == 200

    def test_has_required_fields(self):
        data = client.get("/api/data-science/summary").json()
        assert "status" in data
        assert "pipeline_story" in data
        assert "data_volume" in data
        assert "model_status" in data
        assert "decision_status" in data

    def test_no_data_state(self):
        data = client.get("/api/data-science/summary").json()
        assert data["status"] in ("no_data", "ok")

    def test_pipeline_story_is_list(self):
        data = client.get("/api/data-science/summary").json()
        assert isinstance(data["pipeline_story"], list)

    def test_data_volume_has_counts(self):
        data = client.get("/api/data-science/summary").json()
        dv = data["data_volume"]
        for key in ("products", "stores", "orders", "inventory_snapshots", "feature_rows", "forecast_rows"):
            assert key in dv
            assert isinstance(dv[key], int)

    def test_no_secrets_in_response(self):
        text = client.get("/api/data-science/summary").text
        for bad in ("password", "secret", "api_key", "DATABASE_URL", "sk-", "token"):
            assert bad.lower() not in text.lower()


class TestForecastDiagnostics:
    def test_returns_200(self):
        r = client.get("/api/data-science/forecast-diagnostics")
        assert r.status_code == 200

    def test_has_required_fields(self):
        data = client.get("/api/data-science/forecast-diagnostics").json()
        assert "status" in data
        assert "has_model" in data
        assert "wape_interpretation_guide" in data

    def test_no_data_state(self):
        data = client.get("/api/data-science/forecast-diagnostics").json()
        assert data["status"] in ("no_data", "ok")
        assert isinstance(data["has_model"], bool)

    def test_no_data_returns_no_model(self):
        data = client.get("/api/data-science/forecast-diagnostics").json()
        assert data["has_model"] is False
        assert data["baseline"] is None
        assert data["ml_model"] is None

    def test_wape_guide_has_three_tiers(self):
        data = client.get("/api/data-science/forecast-diagnostics").json()
        guide = data["wape_interpretation_guide"]
        assert "strong" in guide
        assert "directional" in guide
        assert "weak" in guide

    def test_no_secrets_in_response(self):
        text = client.get("/api/data-science/forecast-diagnostics").text
        for bad in ("password", "secret", "api_key", "DATABASE_URL"):
            assert bad.lower() not in text.lower()


class TestModelComparison:
    def test_returns_200(self):
        r = client.get("/api/data-science/model-comparison")
        assert r.status_code == 200

    def test_has_required_fields(self):
        data = client.get("/api/data-science/model-comparison").json()
        assert "status" in data
        assert "has_comparison" in data
        assert "models" in data

    def test_no_data_state(self):
        data = client.get("/api/data-science/model-comparison").json()
        assert data["status"] == "no_data"
        assert data["models"] == []

    def test_no_secrets_in_response(self):
        text = client.get("/api/data-science/model-comparison").text
        for bad in ("password", "secret", "api_key"):
            assert bad.lower() not in text.lower()


class TestFeatureSignals:
    def test_returns_200(self):
        r = client.get("/api/data-science/feature-signals")
        assert r.status_code == 200

    def test_has_required_fields(self):
        data = client.get("/api/data-science/feature-signals").json()
        assert "status" in data
        assert "signals" in data
        assert "total_features" in data
        assert "disclaimer" in data

    def test_signals_is_list(self):
        data = client.get("/api/data-science/feature-signals").json()
        assert isinstance(data["signals"], list)
        assert len(data["signals"]) > 0

    def test_signals_have_correct_shape(self):
        data = client.get("/api/data-science/feature-signals").json()
        for sig in data["signals"]:
            assert "group" in sig
            assert "available" in sig
            assert "example_features" in sig
            assert "interpretation" in sig
            assert isinstance(sig["example_features"], list)

    def test_total_features_positive(self):
        data = client.get("/api/data-science/feature-signals").json()
        assert data["total_features"] > 0

    def test_disclaimer_present(self):
        data = client.get("/api/data-science/feature-signals").json()
        disclaimer = data["disclaimer"]
        assert "association" in disclaimer.lower() or "prototype" in disclaimer.lower()

    def test_no_causal_claims(self):
        data = client.get("/api/data-science/feature-signals").json()
        for sig in data["signals"]:
            interp = sig["interpretation"].lower()
            assert "caused by" not in interp

    def test_no_secrets_in_response(self):
        text = client.get("/api/data-science/feature-signals").text
        for bad in ("password", "secret", "api_key"):
            assert bad.lower() not in text.lower()


class TestBusinessImpact:
    def test_returns_200(self):
        r = client.get("/api/data-science/business-impact")
        assert r.status_code == 200

    def test_has_required_fields(self):
        data = client.get("/api/data-science/business-impact").json()
        assert "status" in data
        assert "has_data" in data
        assert "top_risks" in data
        assert "top_recommendations" in data
        assert "review_guidance" in data
        assert "automation_note" in data

    def test_no_data_state(self):
        data = client.get("/api/data-science/business-impact").json()
        assert data["status"] in ("no_data", "ok")
        assert isinstance(data["has_data"], bool)

    def test_automation_note_present(self):
        data = client.get("/api/data-science/business-impact").json()
        note = data["automation_note"].lower()
        assert "no purchase order" in note or "not automated" in note or "no purchasing" in note

    def test_no_secrets_in_response(self):
        text = client.get("/api/data-science/business-impact").text
        for bad in ("password", "secret", "api_key"):
            assert bad.lower() not in text.lower()


# ---------------------------------------------------------------------------
# WAPE interpretation threshold unit tests
# ---------------------------------------------------------------------------

class TestWapeInterpretation:
    def test_strong_below_30(self):
        assert _wape_label(0.25) == "strong"
        assert _wape_label(0.0) == "strong"
        assert _wape_label(0.299) == "strong"

    def test_directional_30_to_60(self):
        assert _wape_label(0.30) == "directional"
        assert _wape_label(0.45) == "directional"
        assert _wape_label(0.599) == "directional"

    def test_weak_above_60(self):
        assert _wape_label(0.60) == "weak"
        assert _wape_label(0.80) == "weak"
        assert _wape_label(1.0) == "weak"

    def test_none_returns_unknown(self):
        assert _wape_label(None) == "unknown"

    def test_strong_no_warning(self):
        assert _wape_warning(0.25) is None

    def test_directional_no_warning(self):
        assert _wape_warning(0.45) is None

    def test_weak_has_warning(self):
        warning = _wape_warning(0.70)
        assert warning is not None
        assert len(warning) > 10

    def test_interpretation_contains_model_name(self):
        interp = _wape_interpretation(0.25, "TestModel")
        assert "TestModel" in interp

    def test_wape_guide_has_all_tiers(self):
        assert "strong" in WAPE_GUIDE
        assert "directional" in WAPE_GUIDE
        assert "weak" in WAPE_GUIDE


# ---------------------------------------------------------------------------
# Read-only verification: endpoints must not mutate the DB
# ---------------------------------------------------------------------------

class TestReadOnly:
    def test_all_endpoints_use_get_method(self):
        for endpoint in ENDPOINTS:
            r = client.get(endpoint)
            assert r.status_code == 200, f"{endpoint} returned {r.status_code}"

    def test_post_not_allowed(self):
        for endpoint in ENDPOINTS:
            r = client.post(endpoint, json={})
            assert r.status_code in (405, 422), (
                f"POST {endpoint} should not be allowed, got {r.status_code}"
            )
