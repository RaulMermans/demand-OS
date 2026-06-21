"""
Tests for Connector Prep (Sprint 13 Part D).

Requirements:
1. Connector status endpoint exists.
2. Connectors default to disabled.
3. Config validation does not store secrets.
4. Dry-run does not call network.
5. Stub connector implements base interface.
6. No live Shopify/WooCommerce calls occur.
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

def test_connectors_list_exists(client):
    r = client.get("/api/connectors")
    assert r.status_code == 200
    data = r.json()
    assert "connectors" in data
    assert len(data["connectors"]) > 0


def test_connectors_status_exists(client):
    r = client.get("/api/connectors/status")
    assert r.status_code == 200
    data = r.json()
    assert "active_connectors" in data
    assert "disabled_connectors" in data


# -----------------------------------------------------------------------
# 2. Real connectors default to disabled
# -----------------------------------------------------------------------

def test_shopify_disabled_by_default(client):
    r = client.get("/api/connectors")
    connectors = {c["connector_id"]: c for c in r.json()["connectors"]}
    assert "shopify" in connectors
    assert connectors["shopify"]["enabled"] is False
    assert connectors["shopify"]["status"] == "disabled"


def test_woocommerce_disabled_by_default(client):
    r = client.get("/api/connectors")
    connectors = {c["connector_id"]: c for c in r.json()["connectors"]}
    assert "woocommerce" in connectors
    assert connectors["woocommerce"]["enabled"] is False
    assert connectors["woocommerce"]["status"] == "disabled"


def test_connector_status_live_sync_disabled(client):
    r = client.get("/api/connectors/status")
    data = r.json()
    assert data["live_sync_enabled"] is False


# -----------------------------------------------------------------------
# 3. Config validation does not store secrets
# -----------------------------------------------------------------------

def test_shopify_validate_config_no_storage(client):
    r = client.post("/api/connectors/validate-config", json={
        "connector_id": "shopify",
        "config": {
            "SHOPIFY_STORE_URL": "https://myshop.myshopify.com",
            "SHOPIFY_ACCESS_TOKEN": "shpat_secret_token",
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert data["is_valid"] is True
    # Secret must not appear in response
    assert "shpat_secret_token" not in str(data)
    assert data["warning"]  # must include a warning


def test_shopify_validate_config_missing_fields(client):
    r = client.post("/api/connectors/validate-config", json={
        "connector_id": "shopify",
        "config": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["is_valid"] is False
    assert len(data["missing_fields"]) > 0


def test_woocommerce_validate_config(client):
    r = client.post("/api/connectors/validate-config", json={
        "connector_id": "woocommerce",
        "config": {
            "WOO_SITE_URL": "https://mysite.com",
            "WOO_CONSUMER_KEY": "ck_abc",
            "WOO_CONSUMER_SECRET": "cs_secret",
        },
    })
    assert r.status_code == 200
    data = r.json()
    assert data["is_valid"] is True
    assert "cs_secret" not in str(data)


# -----------------------------------------------------------------------
# 4. Dry-run does not call network
# -----------------------------------------------------------------------

def test_shopify_dry_run_no_network(client, monkeypatch):
    # Monkeypatch requests to fail if called
    def _fail_request(*args, **kwargs):
        raise AssertionError("ShopifyConnector dry-run must not make network calls")

    try:
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", _fail_request)
    except ImportError:
        pass

    r = client.post("/api/connectors/dry-run", json={
        "connector_id": "shopify",
        "config": {"SHOPIFY_STORE_URL": "", "SHOPIFY_ACCESS_TOKEN": ""},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "disabled"
    assert "No live API calls" in data["message"]


def test_woocommerce_dry_run_no_network(client):
    r = client.post("/api/connectors/dry-run", json={
        "connector_id": "woocommerce",
        "config": {"WOO_SITE_URL": "", "WOO_CONSUMER_KEY": "", "WOO_CONSUMER_SECRET": ""},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "disabled"


# -----------------------------------------------------------------------
# 5. Stub connectors implement base interface
# -----------------------------------------------------------------------

def test_shopify_connector_raises_not_implemented():
    from app.connectors.shopify import ShopifyConnector
    from datetime import date
    conn = ShopifyConnector()
    with pytest.raises(NotImplementedError):
        conn.fetch_products()
    with pytest.raises(NotImplementedError):
        conn.fetch_orders(date.today(), date.today())


def test_woocommerce_connector_raises_not_implemented():
    from app.connectors.woocommerce import WooCommerceConnector
    from datetime import date
    conn = WooCommerceConnector()
    with pytest.raises(NotImplementedError):
        conn.fetch_products()
    with pytest.raises(NotImplementedError):
        conn.fetch_orders(date.today(), date.today())


def test_shopify_connector_has_validate_config():
    from app.connectors.shopify import ShopifyConnector
    conn = ShopifyConnector()
    result = conn.validate_config({"SHOPIFY_STORE_URL": "x", "SHOPIFY_ACCESS_TOKEN": "y"})
    assert result["is_valid"] is True


def test_shopify_connector_has_dry_run():
    from app.connectors.shopify import ShopifyConnector
    conn = ShopifyConnector()
    result = conn.dry_run({})
    assert result["status"] == "disabled"
    assert isinstance(result["would_fetch"], list)


# -----------------------------------------------------------------------
# 6. No live connector calls in connector list
# -----------------------------------------------------------------------

def test_no_live_calls_in_connector_list(client, monkeypatch):
    """List endpoint must not attempt any network calls."""
    def _fail(*args, **kwargs):
        raise AssertionError("No network calls allowed in connector list")
    try:
        import urllib.request
        monkeypatch.setattr(urllib.request, "urlopen", _fail)
    except ImportError:
        pass
    r = client.get("/api/connectors")
    assert r.status_code == 200
