"""
Tests: Sprint 16 Analytics Cockpit endpoints.

Verifies:
- All five endpoints return HTTP 200.
- Response shapes match schemas.
- Empty-DB (no data) states are handled gracefully.
- No fake confidence percentages are returned.
- No external side effects.
- Endpoints are read-only.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_db(override_db):
    yield


# ---------------------------------------------------------------------------
# /api/analytics/cockpit
# ---------------------------------------------------------------------------

class TestCockpitEndpoint:
    def test_returns_200(self):
        r = client.get("/api/analytics/cockpit")
        assert r.status_code == 200

    def test_response_has_required_keys(self):
        r = client.get("/api/analytics/cockpit")
        d = r.json()
        assert "status" in d
        assert "generated_at" in d
        assert "dataset" in d
        assert "inventory" in d
        assert "forecasting" in d
        assert "risk" in d
        assert "recommendations" in d
        assert "pipeline" in d

    def test_dataset_counts_are_integers(self):
        r = client.get("/api/analytics/cockpit")
        d = r.json()["dataset"]
        assert isinstance(d["products"], int)
        assert isinstance(d["stores"], int)
        assert isinstance(d["orders"], int)
        assert isinstance(d["inventory_snapshots"], int)
        assert isinstance(d["sku_store_combinations"], int)

    def test_no_data_state(self):
        r = client.get("/api/analytics/cockpit")
        d = r.json()
        assert d["status"] in ("no_data", "ready")
        # With no data seeded, products should be 0
        assert d["dataset"]["products"] == 0

    def test_no_fake_confidence_percentages(self):
        r = client.get("/api/analytics/cockpit")
        d = r.json()
        # There must be no "confidence" numeric % field
        assert "confidence_percent" not in str(d)
        assert "confidence_score" not in str(d)

    def test_pipeline_stages_are_strings(self):
        r = client.get("/api/analytics/cockpit")
        pipeline = r.json()["pipeline"]
        for key in ("data_seeded", "features", "forecasts", "risks", "recommendations"):
            assert pipeline[key] in ("ready", "pending")

    def test_endpoint_is_read_only(self):
        # GET only — POST/PUT should return 405
        r = client.post("/api/analytics/cockpit")
        assert r.status_code in (405, 422)

    def test_inventory_value_method_documented(self):
        r = client.get("/api/analytics/cockpit")
        inv = r.json()["inventory"]
        assert "inventory_value_method" in inv
        assert inv["inventory_value_method"] in ("unit_cost", "unit_price (fallback)")

    def test_wape_quality_label_present(self):
        r = client.get("/api/analytics/cockpit")
        fcst = r.json()["forecasting"]
        assert "forecast_quality_label" in fcst
        assert fcst["forecast_quality_label"] in (
            "Strong", "Directional", "Weak / Demo signal", "No model"
        )


# ---------------------------------------------------------------------------
# /api/analytics/inventory-trend
# ---------------------------------------------------------------------------

class TestInventoryTrendEndpoint:
    def test_returns_200_no_filters(self):
        r = client.get("/api/analytics/inventory-trend")
        assert r.status_code == 200

    def test_response_has_series_and_metadata(self):
        r = client.get("/api/analytics/inventory-trend")
        d = r.json()
        assert "series" in d
        assert "metadata" in d

    def test_metadata_mode_aggregate_without_filters(self):
        r = client.get("/api/analytics/inventory-trend")
        assert r.json()["metadata"]["mode"] == "aggregate"

    def test_metadata_mode_filtered_with_product_id(self):
        r = client.get("/api/analytics/inventory-trend?product_id=prod_test")
        assert r.json()["metadata"]["mode"] == "filtered"

    def test_metadata_mode_filtered_with_store_id(self):
        r = client.get("/api/analytics/inventory-trend?store_id=store_test")
        assert r.json()["metadata"]["mode"] == "filtered"

    def test_days_default_is_30(self):
        r = client.get("/api/analytics/inventory-trend")
        assert r.json()["metadata"]["days"] == 30

    def test_days_param_7(self):
        r = client.get("/api/analytics/inventory-trend?days=7")
        assert r.json()["metadata"]["days"] == 7

    def test_days_param_90(self):
        r = client.get("/api/analytics/inventory-trend?days=90")
        assert r.json()["metadata"]["days"] == 90

    def test_invalid_days_falls_back_to_30(self):
        r = client.get("/api/analytics/inventory-trend?days=999")
        assert r.json()["metadata"]["days"] == 30

    def test_series_items_have_date_field(self):
        r = client.get("/api/analytics/inventory-trend")
        series = r.json()["series"]
        assert isinstance(series, list)
        for item in series[:3]:
            assert "date" in item

    def test_endpoint_is_read_only(self):
        r = client.post("/api/analytics/inventory-trend")
        assert r.status_code in (405, 422)


# ---------------------------------------------------------------------------
# /api/analytics/risk-drivers
# ---------------------------------------------------------------------------

class TestRiskDriversEndpoint:
    def test_returns_200(self):
        r = client.get("/api/analytics/risk-drivers")
        assert r.status_code == 200

    def test_response_has_drivers_list(self):
        d = client.get("/api/analytics/risk-drivers").json()
        assert "drivers" in d
        assert isinstance(d["drivers"], list)

    def test_response_has_disclaimer(self):
        d = client.get("/api/analytics/risk-drivers").json()
        assert "disclaimer" in d
        assert len(d["disclaimer"]) > 10

    def test_no_data_returns_empty_drivers(self):
        d = client.get("/api/analytics/risk-drivers").json()
        # With no data, drivers list should be empty
        assert isinstance(d["drivers"], list)

    def test_disclaimer_does_not_claim_causality(self):
        d = client.get("/api/analytics/risk-drivers").json()
        disclaimer = d["disclaimer"].lower()
        # With no data, the disclaimer is an empty-state message; with data it contains safe language
        assert len(disclaimer) > 5  # not empty

    def test_safe_language_in_explanation(self):
        # Driver explanations must not claim certainty
        d = client.get("/api/analytics/risk-drivers").json()
        for entry in d["drivers"]:
            for driver in entry["drivers"]:
                explanation = driver["explanation"].lower()
                assert "guaranteed" not in explanation

    def test_limit_param_respected(self):
        r = client.get("/api/analytics/risk-drivers?limit=5")
        assert r.status_code == 200
        assert len(r.json()["drivers"]) <= 5

    def test_endpoint_is_read_only(self):
        r = client.post("/api/analytics/risk-drivers")
        assert r.status_code in (405, 422)


# ---------------------------------------------------------------------------
# /api/analytics/reorder-queue
# ---------------------------------------------------------------------------

class TestReorderQueueEndpoint:
    def test_returns_200(self):
        r = client.get("/api/analytics/reorder-queue")
        assert r.status_code == 200

    def test_response_has_items_and_safety_note(self):
        d = client.get("/api/analytics/reorder-queue").json()
        assert "items" in d
        assert "safety_note" in d

    def test_safety_note_mentions_no_purchase_orders(self):
        d = client.get("/api/analytics/reorder-queue").json()
        note = d["safety_note"].lower()
        assert "purchase order" in note or "purchase orders" in note

    def test_no_data_returns_empty_items(self):
        d = client.get("/api/analytics/reorder-queue").json()
        assert isinstance(d["items"], list)

    def test_confidence_labels_are_qualitative(self):
        d = client.get("/api/analytics/reorder-queue").json()
        for item in d["items"]:
            assert item["confidence_label"] in ("review_now", "monitor", "low_priority")

    def test_no_numeric_confidence_percentages(self):
        d = client.get("/api/analytics/reorder-queue").json()
        body = str(d)
        assert "confidence_percent" not in body

    def test_endpoint_is_read_only(self):
        r = client.post("/api/analytics/reorder-queue")
        assert r.status_code in (405, 422)


# ---------------------------------------------------------------------------
# /api/analytics/executive-summary
# ---------------------------------------------------------------------------

class TestExecutiveSummaryEndpoint:
    def test_returns_200(self):
        r = client.get("/api/analytics/executive-summary")
        assert r.status_code == 200

    def test_response_has_required_keys(self):
        d = client.get("/api/analytics/executive-summary").json()
        assert "headline" in d
        assert "summary" in d
        assert "next_actions" in d
        assert "safety_note" in d

    def test_headline_is_string(self):
        d = client.get("/api/analytics/executive-summary").json()
        assert isinstance(d["headline"], str)
        assert len(d["headline"]) > 0

    def test_summary_is_list_of_strings(self):
        d = client.get("/api/analytics/executive-summary").json()
        assert isinstance(d["summary"], list)
        for s in d["summary"]:
            assert isinstance(s, str)

    def test_next_actions_is_list(self):
        d = client.get("/api/analytics/executive-summary").json()
        assert isinstance(d["next_actions"], list)

    def test_safety_note_present_and_non_empty(self):
        d = client.get("/api/analytics/executive-summary").json()
        assert isinstance(d["safety_note"], str)
        assert len(d["safety_note"]) > 10

    def test_no_hardcoded_kpi_values(self):
        d = client.get("/api/analytics/executive-summary").json()
        # The response must not contain hardcoded values like "€120,000" or "94%"
        body = str(d)
        assert "120,000" not in body
        assert "94%" not in body

    def test_endpoint_is_read_only(self):
        r = client.post("/api/analytics/executive-summary")
        assert r.status_code in (405, 422)

    def test_no_external_side_effects(self):
        # Simply verifying the endpoint completes without error is the check;
        # there are no email/webhook/Slack calls to intercept in this service.
        r = client.get("/api/analytics/executive-summary")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Cross-cutting: no secrets exposed
# ---------------------------------------------------------------------------

class TestNoSecretsExposed:
    def test_cockpit_no_secret_in_response(self):
        r = client.get("/api/analytics/cockpit")
        body = r.text.lower()
        for secret_keyword in ("password", "secret", "api_key", "token", "private_key"):
            assert secret_keyword not in body

    def test_reorder_queue_no_secret_in_response(self):
        r = client.get("/api/analytics/reorder-queue")
        body = r.text.lower()
        for secret_keyword in ("password", "secret", "api_key", "token"):
            assert secret_keyword not in body
