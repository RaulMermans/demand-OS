"""
Tests: IngestionService persists records to the database correctly.
"""

import pytest
from datetime import date
from sqlalchemy import func

from app.db.models import (
    RawProduct, RawStore, RawOrder, RawInventorySnapshot,
    RawPromotion, RawSupplier, RawPurchaseOrder,
    IngestionRun,
)
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService


TEST_CONFIG = MockConfig(
    seed=42,
    product_count=5,
    store_count=2,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 3, 10),  # 70 days — enough for POs to trigger (~60d of stock)
)


@pytest.fixture
def connector():
    return MockCommerceConnector(TEST_CONFIG)


@pytest.fixture
def service(connector, in_memory_db):
    return IngestionService(connector, in_memory_db)


# ------------------------------------------------------------------
# 1. Basic persistence
# ------------------------------------------------------------------

def test_ingestion_persists_products(service, in_memory_db):
    service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count = in_memory_db.query(func.count(RawProduct.id)).scalar()
    assert count == TEST_CONFIG.product_count


def test_ingestion_persists_stores(service, in_memory_db):
    service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count = in_memory_db.query(func.count(RawStore.id)).scalar()
    assert count == TEST_CONFIG.store_count


def test_ingestion_persists_suppliers(service, in_memory_db):
    service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count = in_memory_db.query(func.count(RawSupplier.id)).scalar()
    assert count > 0


def test_ingestion_persists_orders(service, in_memory_db):
    service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count = in_memory_db.query(func.count(RawOrder.id)).scalar()
    assert count > 0, "Expected orders to be persisted"


def test_ingestion_persists_inventory_snapshots(service, in_memory_db):
    service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count = in_memory_db.query(func.count(RawInventorySnapshot.id)).scalar()
    assert count > 0


def test_ingestion_persists_purchase_orders(service, in_memory_db):
    service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count = in_memory_db.query(func.count(RawPurchaseOrder.id)).scalar()
    assert count > 0


# ------------------------------------------------------------------
# 2. Ingestion run record
# ------------------------------------------------------------------

def test_ingestion_creates_run_record(service, in_memory_db):
    result = service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    run = in_memory_db.query(IngestionRun).filter(IngestionRun.id == result["run_id"]).first()
    assert run is not None
    assert run.status == "success"
    assert run.records_ingested > 0


def test_ingestion_returns_run_id(service):
    result = service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    assert "run_id" in result
    assert result["run_id"]


def test_ingestion_returns_counts(service):
    result = service.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    counts = result["counts"]
    assert counts["products"] == TEST_CONFIG.product_count
    assert counts["stores"] == TEST_CONFIG.store_count
    assert counts["orders"] > 0
    assert counts["inventory_snapshots"] > 0


# ------------------------------------------------------------------
# 3. Idempotency
# ------------------------------------------------------------------

def test_rerunning_same_seed_is_idempotent(connector, in_memory_db):
    svc = IngestionService(connector, in_memory_db)
    svc.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count_first = in_memory_db.query(func.count(RawOrder.id)).scalar()

    svc.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    count_second = in_memory_db.query(func.count(RawOrder.id)).scalar()

    assert count_first == count_second, "Re-running with same seed must not create duplicate orders"


def test_reset_and_seed_clears_then_repopulates(connector, in_memory_db):
    svc = IngestionService(connector, in_memory_db)
    svc.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    before = in_memory_db.query(func.count(RawOrder.id)).scalar()

    svc.reset_and_seed(TEST_CONFIG.start_date, TEST_CONFIG.end_date)
    after = in_memory_db.query(func.count(RawOrder.id)).scalar()

    assert after == before
    assert after > 0


# ------------------------------------------------------------------
# 4. Dry run
# ------------------------------------------------------------------

def test_dry_run_does_not_persist(connector, in_memory_db):
    svc = IngestionService(connector, in_memory_db)
    svc.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date, dry_run=True)
    count = in_memory_db.query(func.count(RawOrder.id)).scalar()
    assert count == 0, "Dry run must not write anything to the DB"


def test_dry_run_returns_counts(connector, in_memory_db):
    svc = IngestionService(connector, in_memory_db)
    result = svc.run(TEST_CONFIG.start_date, TEST_CONFIG.end_date, dry_run=True)
    assert result["status"] == "dry_run"
    assert result["counts"]["products"] > 0
