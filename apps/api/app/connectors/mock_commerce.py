"""
MockCommerceConnector — stub returning empty scaffold responses.

Sprint 1 will replace this with a full synthetic data generator producing
realistic relational e-commerce records (products, stores, orders, inventory,
promotions, suppliers, purchase orders) with configurable seasonality,
promotions, and stockout events.

Reference: g-schumacher44/ecom_sales_data_generator patterns for realistic
relational schema and temporal distributions.
"""

from datetime import date

from app.connectors.base import BaseCommerceConnector
from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
)


class MockCommerceConnector(BaseCommerceConnector):
    """
    Scaffold stub — returns empty lists.

    Sprint 1 TODO: Implement synthetic data generation with:
    - Configurable product catalog (N products, M categories)
    - Multiple stores across regions
    - 2+ years of daily order history with weekday/seasonal patterns
    - Weekly inventory snapshots per product/store
    - Promotion calendar with discount events
    - Supplier catalog with realistic lead times
    - Purchase order history matching demand patterns
    """

    connector_name = "mock"

    def fetch_products(self) -> list[RawProduct]:
        # Sprint 1: generate synthetic product catalog
        return []

    def fetch_stores(self) -> list[RawStore]:
        # Sprint 1: generate synthetic store/channel list
        return []

    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]:
        # Sprint 1: generate synthetic order lines with temporal demand patterns
        return []

    def fetch_inventory_snapshots(
        self, start_date: date, end_date: date
    ) -> list[RawInventorySnapshot]:
        # Sprint 1: generate synthetic inventory snapshots
        return []

    def fetch_promotions(
        self, start_date: date, end_date: date
    ) -> list[RawPromotion]:
        # Sprint 1: generate synthetic promotion calendar
        return []

    def fetch_suppliers(self) -> list[RawSupplier]:
        # Sprint 1: generate synthetic supplier catalog
        return []

    def fetch_purchase_orders(
        self, start_date: date, end_date: date
    ) -> list[RawPurchaseOrder]:
        # Sprint 1: generate synthetic purchase order history
        return []
