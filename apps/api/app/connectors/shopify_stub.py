"""
ShopifyConnector — stub for the Shopify Admin REST/GraphQL connector.

This connector will pull raw operational records from the Shopify API:
  - Products & variants
  - Orders & line items
  - Inventory levels (Inventory API)
  - Discount / promotion codes
  - Suppliers via metafields or connected ERP

Authentication: Shopify OAuth + Admin API key stored in environment variables
(never in the database or source control).  See SECURITY.md.

Sprint 3 TODO: Implement using shopify-api-python or direct httpx calls
against the Shopify Admin REST API (2024-01 version or later).

Required env vars (Sprint 3):
  SHOPIFY_SHOP_DOMAIN=yourstore.myshopify.com
  SHOPIFY_ACCESS_TOKEN=shpat_...
"""

from datetime import date

from app.connectors.base import BaseCommerceConnector
from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
)


class ShopifyConnector(BaseCommerceConnector):
    """
    Scaffold stub — no real API calls are made.

    Sprint 3 TODO: implement Shopify Admin API integration.
    """

    connector_name = "shopify"

    def __init__(self, shop_domain: str = "", access_token: str = ""):
        self.shop_domain = shop_domain
        self.access_token = access_token

    def fetch_products(self) -> list[RawProduct]:
        raise NotImplementedError("ShopifyConnector.fetch_products — Sprint 3")

    def fetch_stores(self) -> list[RawStore]:
        raise NotImplementedError("ShopifyConnector.fetch_stores — Sprint 3")

    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]:
        raise NotImplementedError("ShopifyConnector.fetch_orders — Sprint 3")

    def fetch_inventory_snapshots(
        self, start_date: date, end_date: date
    ) -> list[RawInventorySnapshot]:
        raise NotImplementedError(
            "ShopifyConnector.fetch_inventory_snapshots — Sprint 3"
        )

    def fetch_promotions(
        self, start_date: date, end_date: date
    ) -> list[RawPromotion]:
        raise NotImplementedError("ShopifyConnector.fetch_promotions — Sprint 3")

    def fetch_suppliers(self) -> list[RawSupplier]:
        raise NotImplementedError("ShopifyConnector.fetch_suppliers — Sprint 3")

    def fetch_purchase_orders(
        self, start_date: date, end_date: date
    ) -> list[RawPurchaseOrder]:
        raise NotImplementedError(
            "ShopifyConnector.fetch_purchase_orders — Sprint 3"
        )
