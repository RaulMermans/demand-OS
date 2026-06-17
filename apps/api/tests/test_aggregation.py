"""
Tests: AggregationService and /api/aggregation/* endpoints.

Covers:
  - Reconciliation (sales_daily sums match raw orders)
  - Excluded statuses (cancelled, returned not in sales_daily)
  - days_of_supply formula
  - Promotion daily flags
  - Idempotency (run twice → same rows)
  - product_store_daily completeness
  - Forbidden fields in aggregated tables
  - AggregationRun record created
  - API endpoints: POST /api/aggregation/run, GET /api/aggregation/status
  - data-health includes canonical counts after aggregation
"""

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.main import app
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService
from app.services.aggregation_service import AggregationService
from app.db.models import (
    RawOrder, SalesDaily, InventoryDaily, PromotionDaily,
    ProductStoreDaily, AggregationRun,
)

client = TestClient(app)

AGG_CONFIG = MockConfig(
    seed=42,
    product_count=4,
    store_count=2,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 3, 10),
)

TINY = {"seed": 42, "product_count": 4, "store_count": 2, "history_days": 70}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_db(in_memory_db):
    """Seed raw data, return (db, start_date, end_date)."""
    connector = MockCommerceConnector(AGG_CONFIG)
    IngestionService(connector, in_memory_db).run(AGG_CONFIG.start_date, AGG_CONFIG.end_date)
    return in_memory_db, AGG_CONFIG.start_date, AGG_CONFIG.end_date


@pytest.fixture
def aggregated_db(seeded_db):
    """Seed + aggregate, return (db, result, start_date, end_date)."""
    db, start, end = seeded_db
    result = AggregationService(db).run_full_aggregation(start, end)
    return db, result, start, end


@pytest.fixture(autouse=True)
def fresh_db(override_db):
    yield


# ---------------------------------------------------------------------------
# 1. Basic run
# ---------------------------------------------------------------------------

def test_aggregation_runs_successfully(aggregated_db):
    _, result, *_ = aggregated_db
    assert result["status"] == "success"
    assert "run_id" in result
    assert result["counts"]["sales_daily"] > 0


# ---------------------------------------------------------------------------
# 2. Reconciliation — sales_daily totals match fulfilled raw orders
# ---------------------------------------------------------------------------

def test_sales_daily_totals_match_fulfilled_orders(aggregated_db):
    db, _, start, end = aggregated_db
    fulfilled = (
        db.query(func.sum(RawOrder.quantity))
        .filter(
            RawOrder.order_date >= start,
            RawOrder.order_date <= end,
            RawOrder.status == "fulfilled",
        )
        .scalar() or 0.0
    )
    aggregated = db.query(func.sum(SalesDaily.units_sold)).scalar() or 0.0
    assert abs(fulfilled - aggregated) < 0.01, (
        f"Reconciliation failed: raw fulfilled={fulfilled:.2f}, sales_daily={aggregated:.2f}"
    )


# ---------------------------------------------------------------------------
# 3. Cancelled and returned orders excluded
# ---------------------------------------------------------------------------

def test_cancelled_orders_excluded_from_sales_daily(seeded_db):
    db, start, end = seeded_db
    cancelled_qty = (
        db.query(func.sum(RawOrder.quantity))
        .filter(RawOrder.status == "cancelled",
                RawOrder.order_date >= start, RawOrder.order_date <= end)
        .scalar() or 0.0
    )
    if cancelled_qty == 0:
        pytest.skip("No cancelled orders in this seed — nothing to test")

    AggregationService(db).run_full_aggregation(start, end)

    fulfilled = (
        db.query(func.sum(RawOrder.quantity))
        .filter(RawOrder.status == "fulfilled",
                RawOrder.order_date >= start, RawOrder.order_date <= end)
        .scalar() or 0.0
    )
    aggregated = db.query(func.sum(SalesDaily.units_sold)).scalar() or 0.0
    assert abs(fulfilled - aggregated) < 0.01


def test_returned_orders_excluded_from_sales_daily(seeded_db):
    db, start, end = seeded_db
    returned_qty = (
        db.query(func.sum(RawOrder.quantity))
        .filter(RawOrder.status == "returned",
                RawOrder.order_date >= start, RawOrder.order_date <= end)
        .scalar() or 0.0
    )
    if returned_qty == 0:
        pytest.skip("No returned orders in this seed — nothing to test")

    AggregationService(db).run_full_aggregation(start, end)

    fulfilled = (
        db.query(func.sum(RawOrder.quantity))
        .filter(RawOrder.status == "fulfilled",
                RawOrder.order_date >= start, RawOrder.order_date <= end)
        .scalar() or 0.0
    )
    aggregated = db.query(func.sum(SalesDaily.units_sold)).scalar() or 0.0
    assert abs(fulfilled - aggregated) < 0.01


# ---------------------------------------------------------------------------
# 4. Inventory daily — stockout flags and days_of_supply
# ---------------------------------------------------------------------------

def test_inventory_daily_stockout_flags(aggregated_db):
    db, *_ = aggregated_db
    zero_hand = db.query(InventoryDaily).filter(InventoryDaily.on_hand_units == 0).first()
    if zero_hand is None:
        pytest.skip("No zero-stock snapshots in this window")
    assert zero_hand.stockout_flag is True


def test_days_of_supply_is_positive_or_null(aggregated_db):
    """days_of_supply is either NULL (no recent demand) or a positive number."""
    db, *_ = aggregated_db
    rows = db.query(InventoryDaily).filter(InventoryDaily.days_of_supply.isnot(None)).limit(50).all()
    for row in rows:
        assert row.days_of_supply >= 0, f"Negative days_of_supply: {row.days_of_supply}"


def test_days_of_supply_formula(aggregated_db):
    """Spot-check: for a row with known demand, days_of_supply = on_hand / (total_7d / 7)."""
    from datetime import timedelta
    db, *_ = aggregated_db

    row = db.query(InventoryDaily).filter(
        InventoryDaily.days_of_supply.isnot(None),
        InventoryDaily.on_hand_units > 0,
    ).first()

    if row is None:
        pytest.skip("No inventory rows with computable days_of_supply")

    total_7d = 0.0
    for offset in range(7):
        past = row.date - timedelta(days=offset)
        sd = db.query(SalesDaily).filter(
            SalesDaily.product_id == row.product_id,
            SalesDaily.store_id == row.store_id,
            SalesDaily.date == past,
        ).first()
        if sd:
            total_7d += sd.units_sold

    expected = round(row.on_hand_units / (total_7d / 7), 2)
    assert abs(row.days_of_supply - expected) < 0.1


# ---------------------------------------------------------------------------
# 5. Promotion daily
# ---------------------------------------------------------------------------

def test_promotion_daily_has_rows(aggregated_db):
    db, *_ = aggregated_db
    count = db.query(func.count(PromotionDaily.id)).scalar() or 0
    assert count > 0


def test_promotion_daily_active_rows_exist(aggregated_db):
    db, *_ = aggregated_db
    active = db.query(PromotionDaily).filter(PromotionDaily.is_active == True).first()
    assert active is not None, "Expected at least one active promotion in 70-day window"


# ---------------------------------------------------------------------------
# 6. Idempotency
# ---------------------------------------------------------------------------

def test_aggregation_is_idempotent(seeded_db):
    db, start, end = seeded_db
    svc = AggregationService(db)
    r1 = svc.run_full_aggregation(start, end)
    r2 = svc.run_full_aggregation(start, end)

    assert r1["counts"]["sales_daily"] == r2["counts"]["sales_daily"]
    assert r1["counts"]["inventory_daily"] == r2["counts"]["inventory_daily"]

    final_count = db.query(func.count(SalesDaily.id)).scalar()
    assert final_count == r1["counts"]["sales_daily"]


# ---------------------------------------------------------------------------
# 7. product_store_daily completeness
# ---------------------------------------------------------------------------

def test_product_store_daily_row_count(aggregated_db):
    db, result, start, end = aggregated_db
    from datetime import timedelta
    n_days = (end - start).days + 1
    n_products = AGG_CONFIG.product_count
    n_stores = AGG_CONFIG.store_count
    expected = n_products * n_stores * n_days
    actual = db.query(func.count(ProductStoreDaily.id)).scalar() or 0
    assert actual == expected, f"Expected {expected} rows in product_store_daily, got {actual}"


# ---------------------------------------------------------------------------
# 8. Forbidden fields
# ---------------------------------------------------------------------------

FORBIDDEN = {
    "lag_7d", "lag_14d", "lag_28d", "rolling_mean_28d",
    "forecast", "forecast_7d", "risk_score", "stockout_risk",
    "recommended_units", "reorder_quantity", "target", "future_demand",
}


def test_no_forbidden_fields_in_sales_daily():
    cols = {c.key for c in SalesDaily.__table__.columns}
    assert not (cols & FORBIDDEN), f"Forbidden fields in sales_daily: {cols & FORBIDDEN}"


def test_no_forbidden_fields_in_inventory_daily():
    cols = {c.key for c in InventoryDaily.__table__.columns}
    assert not (cols & FORBIDDEN), f"Forbidden fields in inventory_daily: {cols & FORBIDDEN}"


def test_no_forbidden_fields_in_product_store_daily():
    cols = {c.key for c in ProductStoreDaily.__table__.columns}
    assert not (cols & FORBIDDEN), f"Forbidden fields in product_store_daily: {cols & FORBIDDEN}"


# ---------------------------------------------------------------------------
# 9. AggregationRun record
# ---------------------------------------------------------------------------

def test_aggregation_creates_run_record(aggregated_db):
    db, result, *_ = aggregated_db
    run = db.query(AggregationRun).filter(AggregationRun.id == result["run_id"]).first()
    assert run is not None
    assert run.status == "success"
    assert run.records_produced["sales_daily"] > 0


# ---------------------------------------------------------------------------
# 10. API endpoints
# ---------------------------------------------------------------------------

def test_post_aggregation_run_endpoint():
    client.post("/api/demo/reset", json=TINY)
    response = client.post("/api/aggregation/run", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["counts"]["sales_daily"] > 0


def test_get_aggregation_status_endpoint_not_run():
    response = client.get("/api/aggregation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("not_run", "ready", "failed", "running")
    assert "canonical_counts" in data


def test_get_aggregation_status_after_run():
    client.post("/api/demo/reset", json=TINY)
    client.post("/api/aggregation/run", json={})
    response = client.get("/api/aggregation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["canonical_counts"]["sales_daily"] > 0
    assert data["latest_run"]["status"] == "success"


def test_data_health_shows_canonical_counts_after_aggregation():
    client.post("/api/demo/reset", json=TINY)
    client.post("/api/aggregation/run", json={})
    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert "canonical_counts" in data
    assert data["canonical_counts"]["sales_daily"] > 0
    assert data["canonical_counts"]["inventory_daily"] > 0


def test_aggregation_run_without_data_returns_no_data():
    response = client.post("/api/aggregation/run", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_data"
