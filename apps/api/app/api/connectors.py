"""
Connector prep API — read-only/prep endpoints for real connector architecture.

Real connectors (Shopify, WooCommerce) are DISABLED by default.
No live API calls are made. No credentials are stored.

Endpoints:
  GET  /api/connectors                  — list connectors and their status
  GET  /api/connectors/status           — overall connector health
  POST /api/connectors/validate-config  — validate config shape (no storage)
  POST /api/connectors/dry-run          — simulate connector fetch (no network)
"""

from fastapi import APIRouter, HTTPException
from app.connectors.shopify import ShopifyConnector, SHOPIFY_REQUIRED_CREDENTIALS
from app.connectors.woocommerce import WooCommerceConnector, WOO_REQUIRED_CREDENTIALS
from app.schemas.connectors import (
    ConnectorConfigValidateRequest,
    ConnectorConfigValidateResponse,
    ConnectorDryRunRequest,
    ConnectorDryRunResponse,
)

router = APIRouter()

_CONNECTOR_REGISTRY = [
    {
        "connector_id": "mock_commerce",
        "name": "Mock Commerce",
        "description": "Synthetic data generator. Used for demo and testing.",
        "status": "active",
        "enabled": True,
        "requires_credentials": [],
        "capabilities": ["products", "stores", "orders", "inventory_snapshots",
                         "promotions", "suppliers", "purchase_orders"],
        "note": "Default demo connector. No credentials required.",
    },
    {
        "connector_id": "csv_upload",
        "name": "CSV Upload",
        "description": "Upload raw commerce records as CSV files.",
        "status": "active",
        "enabled": True,
        "requires_credentials": [],
        "capabilities": ["products", "stores", "orders", "inventory_snapshots",
                         "promotions", "suppliers", "purchase_orders"],
        "note": "See /api/csv/templates for upload format.",
    },
    {
        "connector_id": "shopify",
        "name": "Shopify",
        "description": "Shopify Admin API connector (disabled — future sprint).",
        "status": "disabled",
        "enabled": False,
        "requires_credentials": SHOPIFY_REQUIRED_CREDENTIALS,
        "capabilities": ["products", "stores", "orders", "inventory_snapshots",
                         "promotions", "purchase_orders"],
        "note": "Disabled. Enable in a future sprint after configuring credentials.",
    },
    {
        "connector_id": "woocommerce",
        "name": "WooCommerce",
        "description": "WooCommerce REST API v3 connector (disabled — future sprint).",
        "status": "disabled",
        "enabled": False,
        "requires_credentials": WOO_REQUIRED_CREDENTIALS,
        "capabilities": ["products", "stores", "orders", "inventory_snapshots",
                         "promotions"],
        "note": "Disabled. Enable in a future sprint after configuring credentials.",
    },
]


@router.get("/connectors")
def list_connectors() -> dict:
    return {
        "connectors": _CONNECTOR_REGISTRY,
        "total": len(_CONNECTOR_REGISTRY),
        "note": "Real connectors (Shopify, WooCommerce) are disabled. No live sync occurs.",
    }


@router.get("/connectors/status")
def connector_status() -> dict:
    active = [c for c in _CONNECTOR_REGISTRY if c["enabled"]]
    disabled = [c for c in _CONNECTOR_REGISTRY if not c["enabled"]]
    return {
        "active_connectors": [c["connector_id"] for c in active],
        "disabled_connectors": [c["connector_id"] for c in disabled],
        "total_active": len(active),
        "total_disabled": len(disabled),
        "live_sync_enabled": False,
        "note": "No live external API calls are made in this deployment.",
    }


@router.post("/connectors/validate-config")
def validate_connector_config(req: ConnectorConfigValidateRequest) -> dict:
    """Validate connector config shape. No credentials are stored."""
    if req.connector_id == "shopify":
        shopify = ShopifyConnector()
        result = shopify.validate_config(req.config)
        return {
            "connector_id": req.connector_id,
            "is_valid": result["is_valid"],
            "missing_fields": result["missing_fields"],
            "unknown_fields": [],
            "notes": [result["note"]],
            "warning": "Config validation only — no credentials are stored.",
        }
    if req.connector_id == "woocommerce":
        woo = WooCommerceConnector()
        result = woo.validate_config(req.config)
        return {
            "connector_id": req.connector_id,
            "is_valid": result["is_valid"],
            "missing_fields": result["missing_fields"],
            "unknown_fields": [],
            "notes": [result["note"]],
            "warning": "Config validation only — no credentials are stored.",
        }
    raise HTTPException(
        status_code=422,
        detail=f"Config validation not supported for connector '{req.connector_id}'. "
               f"Supported: shopify, woocommerce",
    )


@router.post("/connectors/dry-run")
def connector_dry_run(req: ConnectorDryRunRequest) -> dict:
    """Simulate a connector fetch. No live network calls are made."""
    if req.connector_id == "shopify":
        shopify = ShopifyConnector()
        result = shopify.dry_run(req.config)
        return {
            "connector_id": req.connector_id,
            "status": result["status"],
            "message": result["message"],
            "would_fetch": result["would_fetch"],
            "estimated_record_types": result["would_fetch"],
            "warning": "Dry-run only — no live API calls were made.",
        }
    if req.connector_id == "woocommerce":
        woo = WooCommerceConnector()
        result = woo.dry_run(req.config)
        return {
            "connector_id": req.connector_id,
            "status": result["status"],
            "message": result["message"],
            "would_fetch": result["would_fetch"],
            "estimated_record_types": result["would_fetch"],
            "warning": "Dry-run only — no live API calls were made.",
        }
    raise HTTPException(
        status_code=422,
        detail=f"Dry-run not supported for connector '{req.connector_id}'. "
               f"Supported: shopify, woocommerce",
    )
