"""
Sprint 10C — Foreign-key insert/delete ordering tests.

Verifies that the demo reset/ingestion respects Postgres FK constraints:

1.  raw_suppliers is inserted before raw_products (parent before child).
2.  Every raw_products.supplier_id references an existing raw_suppliers row.
3.  Demo reset succeeds with SQLite FK enforcement enabled (simulates Postgres).
4.  Small demo mode (DEMANDOS_DEMO_SCALE=small) seeds successfully.
5.  Full demo mode seeds successfully locally.
6.  Full demo pipeline reaches at least aggregation in small mode.
"""

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # noqa: F401 — registers all ORM classes on Base.metadata
from app.db.base import Base
from app.db.models import RawProduct, RawStore, RawSupplier, RawPurchaseOrder
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fk_db():
    """
    SQLite in-memory DB with PRAGMA foreign_keys=ON.

    Simulates Postgres FK enforcement so insert-order bugs (products before
    suppliers) are caught without needing a real Postgres connection.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _small_config() -> MockConfig:
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=179)
    return MockConfig(
        seed=42, product_count=10, store_count=2, history_days=180,
        start_date=start, end_date=end,
    )


def _micro_config() -> MockConfig:
    """Tiny dataset for fast FK ordering checks."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=89)
    return MockConfig(
        seed=42, product_count=5, store_count=2, history_days=90,
        start_date=start, end_date=end,
    )


# ---------------------------------------------------------------------------
# 1. Suppliers inserted before products
# ---------------------------------------------------------------------------

def test_suppliers_inserted_before_products(fk_db):
    """
    Insert order: raw_suppliers must be written before raw_products.

    The SQLite PRAGMA foreign_keys=ON fixture catches the same violation
    Postgres raises in production.  If products are inserted first, SQLite
    raises an IntegrityError identical to the Neon/Postgres FK violation.
    """
    config = _micro_config()
    connector = MockCommerceConnector(config)
    svc = IngestionService(connector, fk_db)

    # Should not raise; if products are inserted before suppliers this fails.
    svc.reset_and_seed(config.start_date, config.end_date)

    n_suppliers = fk_db.query(RawSupplier).count()
    n_products = fk_db.query(RawProduct).count()
    assert n_suppliers > 0, "Expected suppliers to be persisted"
    assert n_products == config.product_count


# ---------------------------------------------------------------------------
# 2. Every raw_products.supplier_id references an existing raw_suppliers row
# ---------------------------------------------------------------------------

def test_all_product_supplier_ids_exist(fk_db):
    """Every non-null supplier_id on raw_products must reference raw_suppliers."""
    config = _micro_config()
    connector = MockCommerceConnector(config)
    IngestionService(connector, fk_db).reset_and_seed(config.start_date, config.end_date)

    products = fk_db.query(RawProduct).all()
    supplier_ids = {s.id for s in fk_db.query(RawSupplier).all()}

    missing = [
        p.id for p in products
        if p.supplier_id is not None and p.supplier_id not in supplier_ids
    ]
    assert missing == [], (
        f"Products have dangling supplier_id FK references: {missing}"
    )


# ---------------------------------------------------------------------------
# 3. Reset succeeds with FK enforcement enabled (simulates Postgres)
# ---------------------------------------------------------------------------

def test_reset_and_seed_fk_enforcement(fk_db):
    """reset_and_seed() must complete without IntegrityError when FK checks are on."""
    config = _micro_config()
    connector = MockCommerceConnector(config)
    svc = IngestionService(connector, fk_db)

    result = svc.reset_and_seed(config.start_date, config.end_date)

    assert result["status"] == "ok"
    assert result["counts"]["suppliers"] > 0
    assert result["counts"]["products"] == config.product_count
    assert result["counts"]["stores"] == config.store_count
    assert result["counts"]["orders"] > 0


# ---------------------------------------------------------------------------
# 4. Small demo mode (DEMANDOS_DEMO_SCALE=small) seeds successfully
# ---------------------------------------------------------------------------

def test_small_demo_mode_seeds_successfully(in_memory_db):
    """Small demo scale (10 products, 2 stores, 180 days) seeds without error."""
    config = _small_config()
    connector = MockCommerceConnector(config)
    svc = IngestionService(connector, in_memory_db)

    result = svc.reset_and_seed(config.start_date, config.end_date)

    assert result["status"] == "ok"
    assert result["counts"]["products"] == 10
    assert result["counts"]["stores"] == 2
    assert result["counts"]["suppliers"] > 0
    assert result["counts"]["orders"] > 0
    assert result["counts"]["inventory_snapshots"] > 0


# ---------------------------------------------------------------------------
# 5. Full demo mode still seeds successfully locally
# ---------------------------------------------------------------------------

def test_full_demo_mode_seeds_successfully(in_memory_db):
    """Full demo scale (50 products, 5 stores, 730 days) seeds without error."""
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=729)
    config = MockConfig(
        seed=42, product_count=50, store_count=5, history_days=730,
        start_date=start, end_date=end,
    )
    connector = MockCommerceConnector(config)
    svc = IngestionService(connector, in_memory_db)

    result = svc.reset_and_seed(config.start_date, config.end_date)

    assert result["status"] == "ok"
    assert result["counts"]["products"] == 50
    assert result["counts"]["stores"] == 5
    assert result["counts"]["suppliers"] > 0


# ---------------------------------------------------------------------------
# 6. Full demo pipeline reaches at least aggregation in small mode
# ---------------------------------------------------------------------------

def test_small_mode_pipeline_reaches_aggregation(in_memory_db):
    """
    After a small-mode reset, run_full_pipeline() must reach the aggregation step.

    The pipeline may fail at a later step (e.g. forecasting with sparse data),
    but it must not fail at reset_demo or aggregation.
    """
    from app.services.demo_pipeline_service import DemoPipelineService

    svc = DemoPipelineService(in_memory_db)
    run = svc.run_full_pipeline(
        seed=42, product_count=10, store_count=2, history_days=180,
    )

    step_statuses = {s["step_name"]: s["status"] for s in (run.steps_json or [])}

    assert "reset_demo" in step_statuses, "reset_demo step must be recorded"
    assert step_statuses["reset_demo"] == "completed", (
        f"reset_demo must succeed, got: {step_statuses['reset_demo']}"
    )

    assert "aggregation" in step_statuses, "aggregation step must be recorded"
    assert step_statuses["aggregation"] == "completed", (
        f"aggregation must succeed in small mode, got: {step_statuses['aggregation']}"
    )


# ---------------------------------------------------------------------------
# 7. Delete order is FK-safe (no IntegrityError on second reset)
# ---------------------------------------------------------------------------

def test_double_reset_fk_safe(fk_db):
    """
    Calling reset_and_seed() twice must not raise an FK IntegrityError.

    On the second call, _clear_raw_tables() deletes existing rows and then
    re-inserts them.  The delete order must remove children before parents.
    """
    config = _micro_config()
    connector = MockCommerceConnector(config)
    svc = IngestionService(connector, fk_db)

    svc.reset_and_seed(config.start_date, config.end_date)
    result = svc.reset_and_seed(config.start_date, config.end_date)

    assert result["status"] == "ok"
    assert fk_db.query(RawProduct).count() == config.product_count
    assert fk_db.query(RawSupplier).count() > 0
