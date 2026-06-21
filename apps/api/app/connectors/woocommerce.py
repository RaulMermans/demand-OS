"""
WooCommerceConnector — disabled stub for Sprint 13.

This connector defines the interface for future WooCommerce integration.
It is DISABLED by default and will raise NotImplementedError on any live call.

To enable in a future sprint:
  1. Set WOO_SITE_URL, WOO_CONSUMER_KEY, WOO_CONSUMER_SECRET in environment.
  2. Implement fetch_* methods using the WooCommerce REST API v3.
  3. Add rate limiting, pagination, and incremental sync logic.
  4. Enable via feature flag DEMANDOS_ENABLE_WOOCOMMERCE=true.

Never call live WooCommerce APIs without explicit user opt-in and credentials.
"""

from datetime import date

from app.connectors.base import BaseCommerceConnector
from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine,
    RawInventorySnapshot, RawPromotion, RawSupplier, RawPurchaseOrder,
)

WOO_REQUIRED_CREDENTIALS = ["WOO_SITE_URL", "WOO_CONSUMER_KEY", "WOO_CONSUMER_SECRET"]
WOO_RATE_LIMIT = "WooCommerce default: no hard rate limit; host-dependent"
WOO_PII_FIELDS = ["billing_email", "billing_first_name", "billing_last_name", "billing_address"]


class WooCommerceConnector(BaseCommerceConnector):
    """
    WooCommerce data source connector — DISABLED.

    Status: disabled / stub only.
    Live API calls are not implemented and will not be made.
    """

    connector_name = "woocommerce"
    enabled = False

    def __init__(self) -> None:
        pass

    def _require_enabled(self) -> None:
        raise NotImplementedError(
            "WooCommerceConnector is disabled. "
            "Enable in a future sprint after configuring credentials."
        )

    def fetch_products(self) -> list[RawProduct]:
        self._require_enabled()

    def fetch_stores(self) -> list[RawStore]:
        self._require_enabled()

    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]:
        self._require_enabled()

    def fetch_inventory_snapshots(
        self, start_date: date, end_date: date
    ) -> list[RawInventorySnapshot]:
        self._require_enabled()

    def fetch_promotions(
        self, start_date: date, end_date: date
    ) -> list[RawPromotion]:
        self._require_enabled()

    def fetch_suppliers(self) -> list[RawSupplier]:
        self._require_enabled()

    def fetch_purchase_orders(
        self, start_date: date, end_date: date
    ) -> list[RawPurchaseOrder]:
        self._require_enabled()

    def validate_config(self, config: dict) -> dict:
        """Check that config has required keys. Does not store credentials."""
        missing = [k for k in WOO_REQUIRED_CREDENTIALS if k not in config or not config[k]]
        return {
            "is_valid": len(missing) == 0,
            "missing_fields": missing,
            "note": "Config shape is valid. No credentials stored.",
        }

    def dry_run(self, config: dict) -> dict:
        """Simulate what would happen — no network calls."""
        return {
            "status": "disabled",
            "message": "WooCommerceConnector is disabled. No live API calls made.",
            "would_fetch": [
                "products", "stores", "orders",
                "inventory_snapshots", "promotions", "purchase_orders",
            ],
        }
