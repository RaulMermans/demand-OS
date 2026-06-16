"""
BaseCommerceConnector — protocol/abstract base for all data source connectors.

Every connector must implement these methods and return lists of raw Pydantic
schema objects.  The pipeline never assumes a particular connector — it always
calls the interface, making it trivial to swap mock → CSV → Shopify → ERP.

Rule: connectors return raw operational records only.
      Feature engineering, aggregation, and ML scoring happen downstream.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Protocol, runtime_checkable

from app.schemas.raw import (
    RawProduct,
    RawStore,
    RawOrderLine,
    RawInventorySnapshot,
    RawPromotion,
    RawSupplier,
    RawPurchaseOrder,
)


@runtime_checkable
class CommerceConnectorProtocol(Protocol):
    """Structural protocol — any object implementing these methods qualifies."""

    def fetch_products(self) -> list[RawProduct]: ...
    def fetch_stores(self) -> list[RawStore]: ...
    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]: ...
    def fetch_inventory_snapshots(self, start_date: date, end_date: date) -> list[RawInventorySnapshot]: ...
    def fetch_promotions(self, start_date: date, end_date: date) -> list[RawPromotion]: ...
    def fetch_suppliers(self) -> list[RawSupplier]: ...
    def fetch_purchase_orders(self, start_date: date, end_date: date) -> list[RawPurchaseOrder]: ...


class BaseCommerceConnector(ABC):
    """
    Abstract base class for DemandOS commerce connectors.

    Subclass this for any data source: mock generator, CSV files, Shopify,
    WooCommerce, BigCommerce, ERP systems, data warehouses, etc.

    Design rules
    ------------
    1. Return raw operational records — never compute features, forecasts,
       risk scores, or recommendations inside a connector.
    2. Each record must carry a ``source_connector`` field identifying its origin.
    3. Raise ``NotImplementedError`` for methods that are not yet implemented.
    4. Connectors are stateless across calls; any caching is the connector's
       internal concern and must not leak ML state.
    """

    connector_name: str = "base"

    @abstractmethod
    def fetch_products(self) -> list[RawProduct]:
        """Return all active products from the data source."""
        raise NotImplementedError

    @abstractmethod
    def fetch_stores(self) -> list[RawStore]:
        """Return all stores / channels / locations from the data source."""
        raise NotImplementedError

    @abstractmethod
    def fetch_orders(self, start_date: date, end_date: date) -> list[RawOrderLine]:
        """Return individual order lines (one line per product per order) in date range."""
        raise NotImplementedError

    @abstractmethod
    def fetch_inventory_snapshots(
        self, start_date: date, end_date: date
    ) -> list[RawInventorySnapshot]:
        """Return inventory snapshots in date range."""
        raise NotImplementedError

    @abstractmethod
    def fetch_promotions(
        self, start_date: date, end_date: date
    ) -> list[RawPromotion]:
        """Return promotions active (or starting) within the date range."""
        raise NotImplementedError

    @abstractmethod
    def fetch_suppliers(self) -> list[RawSupplier]:
        """Return all suppliers."""
        raise NotImplementedError

    @abstractmethod
    def fetch_purchase_orders(
        self, start_date: date, end_date: date
    ) -> list[RawPurchaseOrder]:
        """Return purchase orders created or expected within the date range."""
        raise NotImplementedError
