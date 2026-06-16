"""
CsvCommerceConnector — reads raw operational records from CSV files.

Expected CSV layout in data/sample_uploads/:
  products.csv, stores.csv, orders.csv, inventory_snapshots.csv,
  promotions.csv, suppliers.csv, purchase_orders.csv

CSV files must contain raw operational columns only — not precomputed
features, forecasts, or risk scores.

Sprint 2 TODO: Implement CSV parsing with column validation, type coercion,
and automatic mapping of alternate column names from common export formats
(Shopify export, WooCommerce export, generic ERP CSV).
"""

from datetime import date
from pathlib import Path

from app.connectors.base import BaseCommerceConnector
from app.schemas.raw import (
    RawProduct, RawStore, RawOrderLine, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
)

DEFAULT_DATA_DIR = Path("data/sample_uploads")


class CsvCommerceConnector(BaseCommerceConnector):
    """
    Scaffold stub — CSV parsing not yet implemented.

    Sprint 2 TODO: implement pandas read_csv + schema validation.
    """

    connector_name = "csv"

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.data_dir = data_dir

    def fetch_products(self) -> list[RawProduct]:
        raise NotImplementedError("CsvCommerceConnector.fetch_products — Sprint 2")

    def fetch_stores(self) -> list[RawStore]:
        raise NotImplementedError("CsvCommerceConnector.fetch_stores — Sprint 2")

    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]:
        raise NotImplementedError("CsvCommerceConnector.fetch_orders — Sprint 2")

    def fetch_inventory_snapshots(
        self, start_date: date, end_date: date
    ) -> list[RawInventorySnapshot]:
        raise NotImplementedError(
            "CsvCommerceConnector.fetch_inventory_snapshots — Sprint 2"
        )

    def fetch_promotions(
        self, start_date: date, end_date: date
    ) -> list[RawPromotion]:
        raise NotImplementedError("CsvCommerceConnector.fetch_promotions — Sprint 2")

    def fetch_suppliers(self) -> list[RawSupplier]:
        raise NotImplementedError("CsvCommerceConnector.fetch_suppliers — Sprint 2")

    def fetch_purchase_orders(
        self, start_date: date, end_date: date
    ) -> list[RawPurchaseOrder]:
        raise NotImplementedError(
            "CsvCommerceConnector.fetch_purchase_orders — Sprint 2"
        )
