"""
Sprint 10 — Demo Pipeline tests.

Tests:
 1. POST /api/demo/run-full-pipeline endpoint exists (200 or known error)
 2. Full pipeline endpoint is API-key protected when key is configured
 3. Full pipeline endpoint works without key in dev mode
 4. Full pipeline creates a DemoPipelineRun record
 5. Full pipeline records step statuses
 6. Full pipeline completes with status=completed when data is available
 7. Full pipeline stops on failed step (service error injection)
 8. GET /api/demo/pipeline-runs returns list
 9. GET /api/demo/pipeline-runs/latest returns latest or no_runs
10. Latest pipeline run endpoint works after a run
11. Full pipeline does not create external side effects
12. DemoPipelineRun model fields are correct
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.models import DemoPipelineRun


@pytest.fixture
def client(override_db):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_client(override_db):
    """Client with seeded demo data (small dataset for speed)."""
    with TestClient(app) as c:
        c.post("/api/demo/reset", json={
            "seed": 42,
            "product_count": 4,
            "store_count": 2,
            "history_days": 91,
        })
        yield c


# ---------------------------------------------------------------------------
# 1. Endpoint exists
# ---------------------------------------------------------------------------

def test_full_pipeline_endpoint_exists(client):
    """POST /api/demo/run-full-pipeline endpoint exists and accepts JSON."""
    # We don't seed data here — expecting a pipeline failure but not a 404/405.
    resp = client.post("/api/demo/run-full-pipeline", json={})
    assert resp.status_code != 404
    assert resp.status_code != 405


# ---------------------------------------------------------------------------
# 2. API-key protection
# ---------------------------------------------------------------------------

def test_full_pipeline_blocked_without_key_when_configured(client, monkeypatch):
    """POST /api/demo/run-full-pipeline returns 401 when key is configured but absent."""
    from app.config import get_settings, Settings
    s = get_settings()
    new_s = Settings(**{**s.model_dump(), "demandos_api_key": "secret-key"})
    monkeypatch.setattr("app.api.auth.get_settings", lambda: new_s)
    resp = client.post("/api/demo/run-full-pipeline", json={})
    assert resp.status_code == 401


def test_full_pipeline_accepted_with_correct_key(client, monkeypatch):
    """POST /api/demo/run-full-pipeline passes auth when correct key is supplied."""
    from app.config import get_settings, Settings
    s = get_settings()
    new_s = Settings(**{**s.model_dump(), "demandos_api_key": "secret-key"})
    monkeypatch.setattr("app.api.auth.get_settings", lambda: new_s)
    resp = client.post(
        "/api/demo/run-full-pipeline",
        json={"seed": 42, "product_count": 2, "store_count": 1, "history_days": 30},
        headers={"X-DemandOS-API-Key": "secret-key"},
    )
    # May fail due to tiny dataset, but must not be 401
    assert resp.status_code != 401


# ---------------------------------------------------------------------------
# 3. Dev mode (no key configured)
# ---------------------------------------------------------------------------

def test_full_pipeline_allowed_in_dev_mode(client):
    """POST /api/demo/run-full-pipeline is accessible when no API key is configured."""
    resp = client.post("/api/demo/run-full-pipeline", json={
        "seed": 42, "product_count": 2, "store_count": 1, "history_days": 30,
    })
    assert resp.status_code != 401
    assert resp.status_code != 403


# ---------------------------------------------------------------------------
# 4. Creates a DemoPipelineRun record
# ---------------------------------------------------------------------------

def test_full_pipeline_creates_run_record(in_memory_db):
    """run_full_pipeline() creates a DemoPipelineRun row in the database."""
    from app.services.demo_pipeline_service import DemoPipelineService

    count_before = in_memory_db.query(DemoPipelineRun).count()
    svc = DemoPipelineService(in_memory_db)
    # Seed data first for a real run
    from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
    from app.services.ingestion_service import IngestionService
    from datetime import date, timedelta
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=89)
    config = MockConfig(seed=42, product_count=3, store_count=2, history_days=90,
                        start_date=start, end_date=end)
    conn = MockCommerceConnector(config)
    IngestionService(conn, in_memory_db).reset_and_seed(start, end)

    svc.run_full_pipeline(seed=42, product_count=3, store_count=2, history_days=90)

    count_after = in_memory_db.query(DemoPipelineRun).count()
    assert count_after == count_before + 1


# ---------------------------------------------------------------------------
# 5. Records step statuses
# ---------------------------------------------------------------------------

def test_full_pipeline_records_step_statuses(in_memory_db):
    """run_full_pipeline() stores per-step status entries in steps_json."""
    from app.services.demo_pipeline_service import DemoPipelineService, _STEP_NAMES
    from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
    from app.services.ingestion_service import IngestionService
    from datetime import date, timedelta

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=89)
    config = MockConfig(seed=42, product_count=3, store_count=2, history_days=90,
                        start_date=start, end_date=end)
    conn = MockCommerceConnector(config)
    IngestionService(conn, in_memory_db).reset_and_seed(start, end)

    svc = DemoPipelineService(in_memory_db)
    run = svc.run_full_pipeline(seed=42, product_count=3, store_count=2, history_days=90)

    assert run.steps_json is not None
    assert len(run.steps_json) == len(_STEP_NAMES)
    step_names_recorded = {s["step_name"] for s in run.steps_json}
    assert step_names_recorded == set(_STEP_NAMES)


# ---------------------------------------------------------------------------
# 6. Completes successfully with valid data
# ---------------------------------------------------------------------------

def test_full_pipeline_completes_with_seeded_data(in_memory_db):
    """run_full_pipeline() returns status=completed when data is seeded."""
    from app.services.demo_pipeline_service import DemoPipelineService

    svc = DemoPipelineService(in_memory_db)
    run = svc.run_full_pipeline(seed=42, product_count=3, store_count=2, history_days=90)

    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.error_message is None
    for step in run.steps_json:
        assert step["status"] == "completed", f"Step {step['step_name']} not completed: {step}"


# ---------------------------------------------------------------------------
# 7. Stops on failed step
# ---------------------------------------------------------------------------

def test_full_pipeline_stops_on_failed_step(in_memory_db):
    """When a step raises, the run is marked failed and remaining steps are skipped."""
    from app.services.demo_pipeline_service import DemoPipelineService

    svc = DemoPipelineService(in_memory_db)

    original_run_step = svc._run_step

    def broken_aggregation(name, **kwargs):
        if name == "aggregation":
            raise RuntimeError("Simulated aggregation failure")
        return original_run_step(name, **kwargs)

    svc._run_step = broken_aggregation
    run = svc.run_full_pipeline(seed=42, product_count=2, store_count=1, history_days=30)

    assert run.status == "failed"
    assert "aggregation" in (run.error_message or "")

    statuses = {s["step_name"]: s["status"] for s in run.steps_json}
    assert statuses["aggregation"] == "failed"
    # All steps after aggregation should be skipped
    post_aggregation = [n for n in ["features", "baseline_forecast", "train_ml",
                                     "planning_forecast", "stockout_risk", "recommendations"]]
    for name in post_aggregation:
        assert statuses[name] == "skipped", f"{name} should be skipped, got {statuses[name]}"


# ---------------------------------------------------------------------------
# 8. GET /api/demo/pipeline-runs returns list
# ---------------------------------------------------------------------------

def test_pipeline_runs_list_endpoint(client):
    """GET /api/demo/pipeline-runs returns runs list."""
    resp = client.get("/api/demo/pipeline-runs")
    assert resp.status_code == 200
    body = resp.json()
    assert "runs" in body
    assert "total" in body
    assert isinstance(body["runs"], list)


# ---------------------------------------------------------------------------
# 9. GET /api/demo/pipeline-runs/latest returns no_runs when empty
# ---------------------------------------------------------------------------

def test_pipeline_runs_latest_no_runs(client):
    """GET /api/demo/pipeline-runs/latest returns no_runs when no run exists."""
    resp = client.get("/api/demo/pipeline-runs/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "no_runs"
    assert body["run"] is None


# ---------------------------------------------------------------------------
# 10. Latest run endpoint works after a run
# ---------------------------------------------------------------------------

def test_pipeline_runs_latest_after_run(client):
    """GET /api/demo/pipeline-runs/latest returns the most recent run."""
    # Trigger a pipeline run (small dataset; may complete or fail, that's OK)
    client.post("/api/demo/run-full-pipeline", json={
        "seed": 42, "product_count": 3, "store_count": 2, "history_days": 90,
    })
    resp = client.get("/api/demo/pipeline-runs/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run"] is not None
    assert "run_id" in body["run"]
    assert "status" in body["run"]
    assert "steps" in body["run"]


# ---------------------------------------------------------------------------
# 11. No external side effects
# ---------------------------------------------------------------------------

def test_full_pipeline_no_external_calls(in_memory_db):
    """run_full_pipeline() never imports or calls external HTTP libraries."""
    import sys
    http_modules_before = {k for k in sys.modules if "httpx" in k or "requests" in k}

    from app.services.demo_pipeline_service import DemoPipelineService
    svc = DemoPipelineService(in_memory_db)
    svc.run_full_pipeline(seed=42, product_count=2, store_count=1, history_days=30)

    http_modules_after = {k for k in sys.modules if "httpx" in k or "requests" in k}
    # No new HTTP modules should have been imported
    assert http_modules_after == http_modules_before


# ---------------------------------------------------------------------------
# 12. DemoPipelineRun model fields are correct
# ---------------------------------------------------------------------------

def test_demo_pipeline_run_model_fields():
    """DemoPipelineRun has all required fields from the Sprint 10 spec."""
    from app.db.models import DemoPipelineRun
    from sqlalchemy import inspect
    mapper = inspect(DemoPipelineRun)
    column_names = {c.key for c in mapper.mapper.column_attrs}
    required = {"id", "status", "started_at", "completed_at", "current_step",
                "steps_json", "error_message", "created_at"}
    assert required.issubset(column_names), (
        f"Missing DemoPipelineRun fields: {required - column_names}"
    )
