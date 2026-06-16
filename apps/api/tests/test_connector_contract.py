"""
Test: connector contract exists, can be imported, and stubs conform to the interface.
"""

import pytest
from datetime import date
from app.connectors.base import BaseCommerceConnector, CommerceConnectorProtocol
from app.connectors.mock_commerce import MockCommerceConnector
from app.connectors.csv_commerce import CsvCommerceConnector
from app.connectors.shopify_stub import ShopifyConnector


REQUIRED_METHODS = [
    "fetch_products",
    "fetch_stores",
    "fetch_orders",
    "fetch_inventory_snapshots",
    "fetch_promotions",
    "fetch_suppliers",
    "fetch_purchase_orders",
]


@pytest.mark.parametrize("connector_cls", [
    MockCommerceConnector,
    CsvCommerceConnector,
    ShopifyConnector,
])
def test_connector_has_required_methods(connector_cls):
    for method in REQUIRED_METHODS:
        assert hasattr(connector_cls, method), (
            f"{connector_cls.__name__} is missing required method: {method}"
        )


def test_mock_connector_fetch_products_returns_list():
    connector = MockCommerceConnector()
    result = connector.fetch_products()
    assert isinstance(result, list)


def test_mock_connector_fetch_orders_returns_list():
    connector = MockCommerceConnector()
    result = connector.fetch_orders(date(2024, 1, 1), date(2024, 1, 31))
    assert isinstance(result, list)


def test_mock_connector_has_connector_name():
    connector = MockCommerceConnector()
    assert connector.connector_name == "mock"


def test_csv_connector_raises_not_implemented():
    connector = CsvCommerceConnector()
    with pytest.raises(NotImplementedError):
        connector.fetch_products()


def test_shopify_connector_raises_not_implemented():
    connector = ShopifyConnector()
    with pytest.raises(NotImplementedError):
        connector.fetch_products()


def test_mock_connector_is_subclass_of_base():
    assert issubclass(MockCommerceConnector, BaseCommerceConnector)
