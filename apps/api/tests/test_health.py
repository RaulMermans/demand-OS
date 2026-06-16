"""Test: health endpoint returns HTTP 200 with status=ok."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(override_db):
    """Ensure each health test uses an isolated in-memory DB."""
    yield


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data


def test_api_status_returns_scaffold_ready():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scaffold_ready"
    assert data["pipeline_ready"] is False


def test_overview_returns_response():
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    # With no data seeded, status should be no_data
    assert data["status"] in ("scaffold_ready", "no_data", "ok")
    assert "summary" in data


def test_data_health_returns_checks():
    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    # When no data is seeded, status is no_data
    assert data["status"] in ("no_data", "scaffold_ready", "ok", "warning")
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0
