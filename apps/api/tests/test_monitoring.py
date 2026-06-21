"""
Tests for Model Monitoring (Sprint 13 Part B).

Requirements:
1. Monitoring run endpoint exists.
2. Monitoring write endpoint is API-key protected.
3. Monitoring computes latest model metrics.
4. Monitoring computes simple data drift metrics.
5. Monitoring handles no-data state.
6. Monitoring responses expose no secrets.
"""

import pytest
from fastapi.testclient import TestClient

import app.db.models  # noqa: F401
from app.main import app


@pytest.fixture
def client(override_db):
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------------
# 1. Endpoints exist
# -----------------------------------------------------------------------

def test_monitoring_latest_exists(client):
    r = client.get("/api/monitoring/latest")
    assert r.status_code == 200


def test_monitoring_runs_exists(client):
    r = client.get("/api/monitoring/runs")
    assert r.status_code == 200


def test_monitoring_model_exists(client):
    r = client.get("/api/monitoring/model")
    assert r.status_code == 200


def test_monitoring_data_exists(client):
    r = client.get("/api/monitoring/data")
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
# 2. Write endpoint is API-key protected
# -----------------------------------------------------------------------

def test_monitoring_run_requires_api_key(client, monkeypatch):
    _with_key(monkeypatch, "test-key")
    r = client.post("/api/monitoring/run")
    assert r.status_code == 401


def test_monitoring_run_passes_with_key(client, monkeypatch):
    _with_key(monkeypatch, "test-key")
    r = client.post(
        "/api/monitoring/run",
        headers={"X-DemandOS-API-Key": "test-key"},
    )
    assert r.status_code == 200


# -----------------------------------------------------------------------
# 5. Handles no-data state
# -----------------------------------------------------------------------

def test_monitoring_latest_no_data(client):
    r = client.get("/api/monitoring/latest")
    assert r.status_code == 200
    data = r.json()
    assert "has_monitoring_run" in data
    assert data["has_monitoring_run"] is False


def test_monitoring_model_metrics_no_data(client):
    r = client.get("/api/monitoring/model")
    assert r.status_code == 200
    data = r.json()
    assert data["metrics"] == []


def test_monitoring_data_metrics_no_data(client):
    r = client.get("/api/monitoring/data")
    assert r.status_code == 200
    data = r.json()
    assert data["metrics"] == []


# -----------------------------------------------------------------------
# 3 & 4. Run creates metrics after pipeline has data
# -----------------------------------------------------------------------

def test_monitoring_run_creates_run_record(client, in_memory_db):
    from app.db.models import MonitoringRun

    initial_count = in_memory_db.query(MonitoringRun).count()

    r = client.post("/api/monitoring/run")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert "run_id" in data

    after_count = in_memory_db.query(MonitoringRun).count()
    assert after_count > initial_count


def test_monitoring_run_returns_health_statuses(client):
    r = client.post("/api/monitoring/run")
    assert r.status_code == 200
    data = r.json()
    assert "model_health_status" in data
    assert "data_health_status" in data
    assert "overall_status" in data


# -----------------------------------------------------------------------
# 6. No secrets in responses
# -----------------------------------------------------------------------

def test_monitoring_no_secrets_in_responses(client):
    endpoints = [
        "/api/monitoring/latest",
        "/api/monitoring/runs",
        "/api/monitoring/model",
        "/api/monitoring/data",
    ]
    secret_patterns = ["DATABASE_URL", "DEMANDOS_API_KEY", "postgresql://", "sqlite:///",
                       "@neon.tech", "demandos_dev.db"]
    for ep in endpoints:
        r = client.get(ep)
        body = r.text
        for pattern in secret_patterns:
            assert pattern.lower() not in body.lower(), (
                f"Secret pattern '{pattern}' found in {ep}"
            )
