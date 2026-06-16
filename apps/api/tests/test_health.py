"""Test: health endpoint returns HTTP 200 with status=ok."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

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


def test_overview_returns_scaffold_ready():
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scaffold_ready"
    assert "summary" in data


def test_data_health_returns_checks():
    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scaffold_ready"
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0
