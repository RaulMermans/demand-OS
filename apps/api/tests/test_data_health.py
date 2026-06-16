"""
Tests: /api/data-health and /api/demo/reset endpoints return real persisted counts.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TINY_SEED = {"seed": 42, "product_count": 5, "store_count": 2, "history_days": 60}


@pytest.fixture(autouse=True)
def fresh_db(override_db):
    """Each test in this file runs against a clean in-memory DB."""
    yield


def test_data_health_returns_no_data_when_empty():
    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_data"
    assert data["products_count"] == 0
    assert data["orders_count"] == 0
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0


def test_demo_reset_seeds_data():
    response = client.post("/api/demo/reset", json=TINY_SEED)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ingestion"]["counts"]["products"] == 5
    assert data["ingestion"]["counts"]["stores"] == 2
    assert data["ingestion"]["counts"]["orders"] > 0


def test_data_health_returns_real_counts_after_seed():
    client.post("/api/demo/reset", json=TINY_SEED)

    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "warning")
    assert data["products_count"] == 5
    assert data["stores_count"] == 2
    assert data["orders_count"] > 0
    assert data["inventory_snapshots_count"] > 0
    assert data["latest_ingestion_run"] is not None
    assert data["latest_ingestion_run"]["status"] == "success"


def test_data_health_checks_include_required_names_after_seed():
    client.post("/api/demo/reset", json=TINY_SEED)
    response = client.get("/api/data-health")
    data = response.json()
    check_names = {c["name"] for c in data["checks"]}
    assert "referential_integrity" in check_names
    assert "data_seeded" in check_names


def test_demo_reset_twice_produces_same_counts():
    client.post("/api/demo/reset", json=TINY_SEED)
    r1 = client.get("/api/data-health").json()

    client.post("/api/demo/reset", json=TINY_SEED)
    r2 = client.get("/api/data-health").json()

    assert r1["orders_count"] == r2["orders_count"]
    assert r1["products_count"] == r2["products_count"]


def test_ingestion_runs_list():
    client.post("/api/demo/reset", json=TINY_SEED)
    response = client.get("/api/ingestion/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert len(data["runs"]) > 0
    run = data["runs"][0]
    assert run["status"] == "success"
    assert run["records_ingested"] > 0
