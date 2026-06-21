"""
Tests for Scenario Planning (Sprint 13 Part C).

Requirements:
1. Scenario run endpoint exists.
2. Scenario run is API-key protected.
3. Scenario input validation enforces bounds.
4. Scenario results are stored separately.
5. Scenario does not mutate base risk/recommendation tables.
6. Scenario returns before/after deltas.
7. Scenario handles no-data state.
"""

import pytest
from fastapi.testclient import TestClient

import app.db.models  # noqa: F401
from app.main import app


@pytest.fixture
def client(override_db):
    with TestClient(app) as c:
        yield c


VALID_INPUTS = {
    "demand_multiplier": 1.2,
    "lead_time_multiplier": 1.0,
    "supplier_reliability_delta": 0.0,
    "promotion_lift_multiplier": 1.0,
    "inventory_adjustment_units": 0.0,
    "horizon_days": 28,
}


# -----------------------------------------------------------------------
# 1. Endpoints exist
# -----------------------------------------------------------------------

def test_scenario_runs_endpoint_exists(client):
    r = client.get("/api/scenarios/runs")
    assert r.status_code == 200


def test_scenario_latest_endpoint_exists(client):
    r = client.get("/api/scenarios/runs/latest")
    assert r.status_code == 200


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------

def _with_key(monkeypatch, key: str):
    from app.config import Settings, get_settings
    s = get_settings()
    new_s = Settings(**{**s.model_dump(), "demandos_api_key": key})
    monkeypatch.setattr("app.api.auth.get_settings", lambda: new_s)


# -----------------------------------------------------------------------
# 2. API key protection
# -----------------------------------------------------------------------

def test_scenario_run_requires_api_key(client, monkeypatch):
    _with_key(monkeypatch, "test-key")
    r = client.post("/api/scenarios/run", json=VALID_INPUTS)
    assert r.status_code == 401


def test_scenario_run_passes_with_key(client, monkeypatch):
    _with_key(monkeypatch, "test-key")
    r = client.post(
        "/api/scenarios/run",
        json=VALID_INPUTS,
        headers={"X-DemandOS-API-Key": "test-key"},
    )
    assert r.status_code == 200


# -----------------------------------------------------------------------
# 3. Input validation enforces bounds
# -----------------------------------------------------------------------

@pytest.mark.parametrize("field,bad_value", [
    ("demand_multiplier", 0.1),
    ("demand_multiplier", 3.0),
    ("lead_time_multiplier", 0.1),
    ("lead_time_multiplier", 3.0),
    ("supplier_reliability_delta", -0.5),
    ("supplier_reliability_delta", 0.5),
    ("promotion_lift_multiplier", 0.1),
    ("horizon_days", 15),   # not in allowed set
    ("horizon_days", 100),
])
def test_scenario_input_validation(client, field, bad_value):
    bad_inputs = {**VALID_INPUTS, field: bad_value}
    r = client.post("/api/scenarios/run", json=bad_inputs)
    assert r.status_code == 422


def test_scenario_valid_horizon_values(client):
    for horizon in [7, 14, 28, 56, 90]:
        inputs = {**VALID_INPUTS, "horizon_days": horizon}
        r = client.post("/api/scenarios/run", json=inputs)
        assert r.status_code == 200


# -----------------------------------------------------------------------
# 4. Results stored separately
# -----------------------------------------------------------------------

def test_scenario_results_stored_in_separate_table(client, in_memory_db):
    from app.db.models import ScenarioRun, ReorderRecommendation, StockoutRisk

    initial_rec_count = in_memory_db.query(ReorderRecommendation).count()
    initial_risk_count = in_memory_db.query(StockoutRisk).count()

    r = client.post("/api/scenarios/run", json=VALID_INPUTS)
    assert r.status_code == 200
    data = r.json()

    # Scenario run record exists
    run = in_memory_db.query(ScenarioRun).filter(
        ScenarioRun.id == data["scenario_id"]
    ).first()
    assert run is not None
    assert run.status == "completed"

    # Production tables not touched
    assert in_memory_db.query(ReorderRecommendation).count() == initial_rec_count
    assert in_memory_db.query(StockoutRisk).count() == initial_risk_count


# -----------------------------------------------------------------------
# 5. Does not mutate base tables
# -----------------------------------------------------------------------

def test_scenario_does_not_mutate_canonical_tables(client, in_memory_db):
    from app.db.models import StockoutRisk, StockoutRiskRun, ReorderRecommendation

    count_before = (
        in_memory_db.query(StockoutRisk).count()
        + in_memory_db.query(StockoutRiskRun).count()
        + in_memory_db.query(ReorderRecommendation).count()
    )

    for _ in range(3):
        client.post("/api/scenarios/run", json=VALID_INPUTS)

    count_after = (
        in_memory_db.query(StockoutRisk).count()
        + in_memory_db.query(StockoutRiskRun).count()
        + in_memory_db.query(ReorderRecommendation).count()
    )

    assert count_before == count_after, "Scenario runs must not mutate canonical tables"


# -----------------------------------------------------------------------
# 6. Returns before/after deltas
# -----------------------------------------------------------------------

def test_scenario_returns_deltas(client):
    r = client.post("/api/scenarios/run", json=VALID_INPUTS)
    assert r.status_code == 200
    data = r.json()

    assert "baseline_summary" in data
    assert "scenario_summary" in data
    assert "delta_lost_sales" in data
    assert "delta_high_risk_count" in data
    assert "delta_critical_risk_count" in data
    assert data["simulated"] is True


# -----------------------------------------------------------------------
# 7. Handles no-data state
# -----------------------------------------------------------------------

def test_scenario_latest_no_data(client):
    r = client.get("/api/scenarios/runs/latest")
    assert r.status_code == 200
    data = r.json()
    assert data["has_scenario_run"] is False


def test_scenario_runs_empty(client):
    r = client.get("/api/scenarios/runs")
    assert r.status_code == 200
    data = r.json()
    assert data["runs"] == []


def test_scenario_get_by_id_not_found(client):
    r = client.get("/api/scenarios/nonexistent-id")
    assert r.status_code == 404


def test_scenario_simulated_label(client):
    r = client.post("/api/scenarios/run", json=VALID_INPUTS)
    data = r.json()
    assert data.get("simulated") is True

    r2 = client.get("/api/scenarios/runs")
    runs = r2.json()["runs"]
    assert all(run.get("simulated") is True for run in runs)
