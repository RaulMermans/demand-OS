"""
Tests for Sprint 6 — Stockout Risk Engine.

Coverage:
  1.  StockoutService runs with a valid forecast run
  2.  Stockout risk run metadata is persisted
  3.  Stockout risk rows are persisted
  4.  Current inventory is read from latest inventory_daily as of date
  5.  Inbound purchase orders within horizon are included
  6.  Purchase orders outside horizon are excluded
  7.  Supplier lead time is joined correctly
  8.  Forecast demand p50 is summed over horizon
  9.  Forecast demand p90 fallback works when p90 is null
  10. Days of supply formula is correct
  11. Projected end inventory formula is correct
  12. Safety stock formula is correct
  13. Lost sales units/value formulas are correct
  14. Critical tier triggers when stockout occurs before lead-time coverage
  15. High tier triggers when p50 demand exceeds available inventory
  16. Medium tier triggers when p90/safety-stock condition is weak
  17. Low tier triggers when inventory safely covers demand
  18. Unknown tier triggers when required data is missing
  19. Risk score is bounded 0–100
  20. Risk API POST /api/risks/run works
  21. Risk API GET /api/risks/latest works
  22. Risk API GET /api/risks supports ranking/filtering
  23. Risk API GET /api/risks/product/{product_id} works
  24. Data-health includes real risk counts
  25. Overview includes honest risk metrics only
  26. No reorder recommendation fields are introduced
  27. Risk run is idempotent / clear-before-rewrite safe
  28. Historical simulation mode is clearly marked
  29. Forward planning mode errors clearly if no usable forecast exists
  30. Existing Sprint 0–5 tests still pass (guard)
  31. Planning forecast endpoint generates forward-looking rows
  32. Forward planning runs tagged mode=forward_planning
"""

import math
import uuid
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.db.models import (
    ForecastRun, Forecast, InventoryDaily, RawPurchaseOrder,
    RawProduct, RawSupplier, RawStore, FeatureMatrix, FeatureRun,
    StockoutRisk, StockoutRiskRun, ReorderRecommendation,
)
from app.services.stockout_service import StockoutService


# ---------------------------------------------------------------------------
# Helpers — minimal fixture builders
# ---------------------------------------------------------------------------

def _insert_product(db, product_id="prod-1", supplier_id="sup-1", unit_price=50.0, category="Tops"):
    db.add(RawProduct(
        id=product_id, external_id=f"ext-{product_id}", sku=f"SKU-{product_id}",
        name=f"Product {product_id}", category=category,
        supplier_id=supplier_id, unit_price=unit_price, unit_cost=25.0,
        source_connector="mock",
    ))
    db.flush()


def _insert_store(db, store_id="store-1"):
    db.add(RawStore(
        id=store_id, external_id=f"ext-{store_id}",
        name=f"Store {store_id}", channel="retail",
        source_connector="mock",
    ))
    db.flush()


def _insert_supplier(db, supplier_id="sup-1", lead_min=5, lead_max=10, reliability=0.9):
    db.add(RawSupplier(
        id=supplier_id, external_id=f"ext-{supplier_id}",
        name=f"Supplier {supplier_id}", country="ES",
        lead_time_days_min=lead_min, lead_time_days_max=lead_max,
        reliability_score=reliability, source_connector="mock",
    ))
    db.flush()


def _insert_inventory(db, product_id="prod-1", store_id="store-1", d=None, on_hand=100.0):
    d = d or date(2024, 1, 15)
    db.add(InventoryDaily(
        id=f"invd-{product_id}-{store_id}-{d}",
        product_id=product_id, store_id=store_id,
        date=d, on_hand_units=on_hand, on_order_units=0.0,
        inbound_units=0.0, stockout_flag=(on_hand == 0),
    ))
    db.flush()


def _insert_po(db, product_id="prod-1", store_id="store-1",
               delivery_date=None, qty=50.0, status="confirmed"):
    po_id = str(uuid.uuid4())
    delivery_date = delivery_date or date(2024, 1, 20)
    db.add(RawPurchaseOrder(
        id=po_id, external_po_id=f"po-{po_id}",
        supplier_id="sup-1", product_id=product_id, store_id=store_id,
        ordered_at=datetime.utcnow(), expected_delivery_date=delivery_date,
        quantity_ordered=qty, unit_cost=25.0, status=status,
        source_connector="mock",
    ))
    db.flush()


def _insert_feature_row(db, product_id="prod-1", store_id="store-1",
                         d=None, std_7d=5.0, mean_7d=10.0, lag_7d=10.0):
    d = d or date(2024, 1, 14)
    db.add(FeatureMatrix(
        id=str(uuid.uuid4()),
        date=d, product_id=product_id, store_id=store_id,
        target_units_sold=10.0,
        lag_units_7d=lag_7d, lag_units_1d=lag_7d,
        rolling_units_mean_7d=mean_7d, rolling_units_std_7d=std_7d,
        rolling_units_mean_28d=mean_7d, rolling_units_std_28d=std_7d,
        retail_price=50.0, unit_cost=25.0, gross_margin_pct=0.5,
        available_units=100.0, stockout_flag=False, days_of_supply=10.0,
        category="Tops", store_channel="retail",
        days_since_launch=100, product_age_bucket="mature_91_365",
        day_of_week=0, week_of_year=3, month=1, quarter=1, is_weekend=False,
        promo_active=False, discount_pct=0.0,
        feature_run_id="feat-run-1", created_at=datetime.utcnow(),
    ))
    db.flush()


def _insert_forecast_run(db, run_id=None, model_type="seasonal_naive",
                          mode="forward_planning", backtest_mode=False,
                          test_start=None, test_end=None):
    run_id = run_id or f"frun-{uuid.uuid4()}"
    test_start = test_start or date(2024, 1, 16)
    test_end = test_end or date(2024, 2, 12)
    db.add(ForecastRun(
        id=run_id, model_name=model_type, model_type=model_type,
        horizon_days=28, backtest_mode=backtest_mode, mode=mode,
        status="completed", started_at=datetime.utcnow(),
        test_start_date=test_start, test_end_date=test_end,
    ))
    db.flush()
    return run_id


def _insert_forecasts(db, run_id, product_id="prod-1", store_id="store-1",
                       start_date=None, days=28, p50=10.0, p90=None):
    start_date = start_date or date(2024, 1, 16)
    for day in range(days):
        fc_date = start_date + timedelta(days=day)
        p90_val = p90 if p90 is not None else p50 + 5.0
        db.add(Forecast(
            id=str(uuid.uuid4()),
            forecast_run_id=run_id,
            forecast_date=fc_date,
            product_id=product_id, store_id=store_id,
            horizon_day=day + 1, model_name="seasonal_naive",
            model_type="seasonal_naive",
            p50_units=p50, p90_units=p90_val, p10_units=max(0.0, p50 - 5.0),
            actual_units=None,
        ))
    db.flush()


# ---------------------------------------------------------------------------
# Test 1: StockoutService runs with a valid forecast run
# ---------------------------------------------------------------------------

def test_stockout_service_runs_with_valid_forecast(in_memory_db):
    """Service completes without error when all data is present."""
    db = in_memory_db
    _insert_supplier(db)
    _insert_product(db)
    _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15))
    run_id = _insert_forecast_run(db, mode="forward_planning", backtest_mode=False,
                                   test_start=date(2024, 1, 16), test_end=date(2024, 2, 12))
    _insert_forecasts(db, run_id, start_date=date(2024, 1, 16), days=28)
    _insert_feature_row(db)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id, horizon_days=28,
                                    mode="forward_planning")
    assert result["status"] == "completed"
    assert result["rows_created"] > 0


# ---------------------------------------------------------------------------
# Test 2: Stockout risk run metadata is persisted
# ---------------------------------------------------------------------------

def test_risk_run_metadata_persisted(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15))
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risk_run = db.query(StockoutRiskRun).filter(
        StockoutRiskRun.id == result["risk_run_id"]
    ).first()
    assert risk_run is not None
    assert risk_run.status == "completed"
    assert risk_run.rows_created > 0
    assert risk_run.risk_horizon_days == 28
    assert risk_run.as_of_date is not None


# ---------------------------------------------------------------------------
# Test 3: Stockout risk rows are persisted
# ---------------------------------------------------------------------------

def test_risk_rows_persisted(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15))
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert len(risks) > 0
    r = risks[0]
    assert r.product_id == "prod-1"
    assert r.store_id == "store-1"
    assert r.risk_tier in {"critical", "high", "medium", "low", "unknown"}


# ---------------------------------------------------------------------------
# Test 4: Current inventory is read from latest inventory_daily as of date
# ---------------------------------------------------------------------------

def test_reads_latest_inventory_as_of_date(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    # Two inventory rows — should use the most recent one on or before as_of_date
    _insert_inventory(db, d=date(2024, 1, 10), on_hand=200.0)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=80.0)
    run_id = _insert_forecast_run(db, test_start=date(2024, 1, 16))
    _insert_forecasts(db, run_id, start_date=date(2024, 1, 16))

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    assert r.current_on_hand_units == pytest.approx(80.0)


# ---------------------------------------------------------------------------
# Test 5: Inbound POs within horizon are included
# ---------------------------------------------------------------------------

def test_inbound_pos_within_horizon_included(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=50.0)
    # PO within horizon: delivery on Jan 20 (within 28d of Jan 15)
    _insert_po(db, delivery_date=date(2024, 1, 20), qty=30.0, status="confirmed")
    run_id = _insert_forecast_run(db, test_start=date(2024, 1, 16))
    _insert_forecasts(db, run_id, start_date=date(2024, 1, 16), p50=3.0)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert any(r.inbound_units_within_horizon == pytest.approx(30.0) for r in risks)


# ---------------------------------------------------------------------------
# Test 6: POs outside horizon are excluded
# ---------------------------------------------------------------------------

def test_pos_outside_horizon_excluded(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=100.0)
    # PO outside horizon: delivery 60 days out (beyond 28d)
    _insert_po(db, delivery_date=date(2024, 3, 20), qty=50.0, status="confirmed")
    run_id = _insert_forecast_run(db, test_start=date(2024, 1, 16))
    _insert_forecasts(db, run_id, start_date=date(2024, 1, 16), p50=2.0)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert all(r.inbound_units_within_horizon == pytest.approx(0.0) for r in risks)


# ---------------------------------------------------------------------------
# Test 7: Supplier lead time is joined correctly
# ---------------------------------------------------------------------------

def test_supplier_lead_time_joined(in_memory_db):
    db = in_memory_db
    _insert_supplier(db, lead_min=5, lead_max=14)
    _insert_product(db)
    _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15))
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert risks[0].supplier_lead_time_days == 14  # uses lead_time_days_max


# ---------------------------------------------------------------------------
# Test 8: Forecast demand p50 is summed over horizon
# ---------------------------------------------------------------------------

def test_forecast_demand_p50_summed(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=500.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=5.0)  # 28 * 5 = 140

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    assert r.forecast_demand_p50 == pytest.approx(28 * 5.0)


# ---------------------------------------------------------------------------
# Test 9: Forecast demand p90 fallback when p90 is null
# ---------------------------------------------------------------------------

def test_p90_fallback_to_p50_when_null(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=500.0)
    run_id = _insert_forecast_run(db)
    # Insert forecasts with p90_units=None
    run_id2 = _insert_forecast_run(db, run_id=f"frun-null-p90-{uuid.uuid4()}")
    for day in range(28):
        fc_date = date(2024, 1, 16) + timedelta(days=day)
        db.add(Forecast(
            id=str(uuid.uuid4()), forecast_run_id=run_id2,
            forecast_date=fc_date, product_id="prod-1", store_id="store-1",
            horizon_day=day+1, model_name="seasonal_naive", model_type="seasonal_naive",
            p50_units=7.0, p90_units=None, p10_units=4.0, actual_units=None,
        ))
    db.flush()

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id2)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    # p90 should fall back to p50 sum when p90_units is null
    assert r.forecast_demand_p90 == pytest.approx(28 * 7.0)


# ---------------------------------------------------------------------------
# Test 10: Days of supply formula is correct
# ---------------------------------------------------------------------------

def test_days_of_supply_formula(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=140.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=5.0)  # avg=5, supply=140/5=28

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    assert r.days_of_supply == pytest.approx(28.0)


# ---------------------------------------------------------------------------
# Test 11: Projected end inventory formula is correct
# ---------------------------------------------------------------------------

def test_projected_end_inventory_formula(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=100.0)
    _insert_po(db, delivery_date=date(2024, 1, 20), qty=20.0, status="confirmed")
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=4.0, p90=6.0)
    # p50 demand = 112, p90 demand = 168
    # proj_p50 = 100 + 20 - 112 = 8
    # proj_p90 = 100 + 20 - 168 = -48

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    assert r.projected_end_inventory_p50 == pytest.approx(100.0 + 20.0 - 28 * 4.0, abs=1e-3)
    assert r.projected_end_inventory_p90 == pytest.approx(100.0 + 20.0 - 28 * 6.0, abs=1e-3)


# ---------------------------------------------------------------------------
# Test 12: Safety stock formula is correct
# ---------------------------------------------------------------------------

def test_safety_stock_formula(in_memory_db):
    db = in_memory_db
    _insert_supplier(db, lead_max=9)  # lead_time=9 days
    _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=200.0)
    # std_7d=4.0 → safety_stock = 1.65 * 4.0 * sqrt(9) = 1.65 * 4 * 3 = 19.8
    _insert_feature_row(db, std_7d=4.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=5.0)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    expected_ss = 1.65 * 4.0 * math.sqrt(9)
    assert risks[0].safety_stock_units == pytest.approx(expected_ss, rel=1e-3)


# ---------------------------------------------------------------------------
# Test 13: Lost sales units/value formulas are correct
# ---------------------------------------------------------------------------

def test_lost_sales_formulas(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db, unit_price=50.0); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=50.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=5.0)
    # forecast_p50=140, available=50, inbound=0
    # lost_units = max(0, 140 - 50) = 90
    # lost_value = 90 * 50 = 4500

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    assert r.lost_sales_units_estimate == pytest.approx(90.0)
    assert r.lost_sales_value_estimate == pytest.approx(90.0 * 50.0)


# ---------------------------------------------------------------------------
# Test 14: Critical tier triggers when stockout before lead-time
# ---------------------------------------------------------------------------

def test_critical_tier_triggers(in_memory_db):
    db = in_memory_db
    _insert_supplier(db, lead_max=14)  # lead_time=14 days
    _insert_product(db)
    _insert_store(db)
    # Very low inventory vs high demand → stockout within lead time
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=10.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=10.0)  # total demand=280
    # avg_daily=10, days_until_stockout = 10/10 = 1 day → 1 <= min(7,14)=7 → critical

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert any(r.risk_tier == "critical" for r in risks)


# ---------------------------------------------------------------------------
# Test 15: High tier triggers when p50 demand exceeds inventory
# ---------------------------------------------------------------------------

def test_high_tier_triggers(in_memory_db):
    db = in_memory_db
    _insert_supplier(db, lead_max=3)
    _insert_product(db)
    _insert_store(db)
    # Moderate inventory vs demand: p50 > available but not critically so
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=50.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=4.0)
    # total p50=112 > available=50 → proj_p50 = -62 → high
    # avg=4 → days_until_stockout=50/4=12.5 > min(7,3)=3 → not critical

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    r = risks[0]
    assert r.risk_tier in {"critical", "high"}
    # Check that proj_p50 is negative
    assert r.projected_end_inventory_p50 < 0


# ---------------------------------------------------------------------------
# Test 16: Medium tier triggers when p90/safety-stock condition is weak
# ---------------------------------------------------------------------------

def test_medium_tier_triggers(in_memory_db):
    db = in_memory_db
    # Large safety stock, but p90 projection just squeaks by
    _insert_supplier(db, lead_max=25)  # long lead time → high safety stock
    _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=400.0)
    # std=10 → safety_stock = 1.65 * 10 * sqrt(25) = 82.5
    _insert_feature_row(db, std_7d=10.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=5.0, p90=12.0)
    # p50_demand=140, p90_demand=336
    # proj_p50 = 400-140=260 (positive → not high)
    # proj_p90 = 400-336=64 < safety_stock=82.5 → medium

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert any(r.risk_tier == "medium" for r in risks)


# ---------------------------------------------------------------------------
# Test 17: Low tier triggers when inventory safely covers demand
# ---------------------------------------------------------------------------

def test_low_tier_triggers(in_memory_db):
    db = in_memory_db
    _insert_supplier(db, lead_max=7); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=1000.0)
    _insert_feature_row(db, std_7d=2.0)  # small std → small safety stock
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=3.0, p90=5.0)
    # p50=84, p90=140
    # proj_p50 = 916, proj_p90 = 860
    # safety_stock = 1.65*2*sqrt(7) ≈ 8.7
    # coverage = 1000/84 ≈ 11.9 >> 1.25 → low

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert any(r.risk_tier == "low" for r in risks)


# ---------------------------------------------------------------------------
# Test 18: Unknown tier triggers when required data is missing
# ---------------------------------------------------------------------------

def test_unknown_tier_when_no_inventory(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    # No inventory_daily rows inserted → missing inventory data
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    assert any(r.risk_tier == "unknown" for r in risks)


# ---------------------------------------------------------------------------
# Test 19: Risk score is bounded 0–100
# ---------------------------------------------------------------------------

def test_risk_score_bounded(in_memory_db):
    db = in_memory_db
    _insert_supplier(db, reliability=0.5); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=1.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=100.0)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(forecast_run_id=run_id)

    risks = db.query(StockoutRisk).filter(
        StockoutRisk.risk_run_id == result["risk_run_id"]
    ).all()
    for r in risks:
        if r.risk_score is not None:
            assert 0.0 <= r.risk_score <= 100.0


# ---------------------------------------------------------------------------
# API tests (Tests 20–25)
# Use the full pipeline via API endpoints (POST /api/demo/reset etc.)
# to avoid cross-session isolation issues with the patched in-memory DB.
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from app.main import app

api_client = TestClient(app)

_SMALL_RESET = {"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91}


def _run_full_pipeline(client):
    """Run the minimal pipeline needed for stockout risk scoring."""
    client.post("/api/demo/reset", json=_SMALL_RESET)
    client.post("/api/aggregation/run")
    client.post("/api/features/build")
    client.post("/api/forecasts/baseline/run", json={"model_type": "seasonal_naive"})
    # Run planning forecast so forward_planning mode is available
    client.post("/api/forecasts/planning/run", json={"model_type": "seasonal_naive", "horizon_days": 28})


# ---------------------------------------------------------------------------
# Test 20: POST /api/risks/run
# ---------------------------------------------------------------------------

def test_api_risks_run(override_db):
    _run_full_pipeline(api_client)
    resp = api_client.post("/api/risks/run", json={
        "horizon_days": 28,
        "mode": "forward_planning",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert "risk_run_id" in body
    assert "risk_counts" in body
    assert "rows_created" in body
    assert body["rows_created"] > 0


# ---------------------------------------------------------------------------
# Test 21: GET /api/risks/latest
# ---------------------------------------------------------------------------

def test_api_risks_latest(override_db):
    _run_full_pipeline(api_client)
    api_client.post("/api/risks/run", json={"horizon_days": 28})

    resp = api_client.get("/api/risks/latest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["run"] is not None
    assert "sample" in body


# ---------------------------------------------------------------------------
# Test 22: GET /api/risks supports ranking/filtering
# ---------------------------------------------------------------------------

def test_api_risks_list_with_filter(override_db):
    _run_full_pipeline(api_client)
    api_client.post("/api/risks/run", json={"horizon_days": 28})

    resp = api_client.get("/api/risks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "rows" in body
    assert "risk_counts" in body

    # Filter by tier — verify only matching rows returned
    for tier in ["low", "high", "medium", "critical"]:
        resp2 = api_client.get(f"/api/risks?risk_tier={tier}")
        assert resp2.status_code == 200
        body2 = resp2.json()
        for row in body2["rows"]:
            assert row["risk_tier"] == tier


# ---------------------------------------------------------------------------
# Test 23: GET /api/risks/product/{product_id}
# ---------------------------------------------------------------------------

def test_api_risks_product(override_db):
    _run_full_pipeline(api_client)
    api_client.post("/api/risks/run", json={"horizon_days": 28})

    # Get a product_id from the risk list
    resp = api_client.get("/api/risks?limit=1")
    rows = resp.json().get("rows", [])
    if not rows:
        pytest.skip("No risk rows available to test product endpoint")

    product_id = rows[0]["product_id"]
    resp2 = api_client.get(f"/api/risks/product/{product_id}")
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["status"] == "ok"
    assert body["product_id"] == product_id
    assert "rows" in body


# ---------------------------------------------------------------------------
# Test 24: Data-health includes real risk counts
# ---------------------------------------------------------------------------

def test_data_health_includes_risk_counts(override_db):
    _run_full_pipeline(api_client)
    api_client.post("/api/risks/run", json={"horizon_days": 28})

    resp = api_client.get("/api/data-health")
    assert resp.status_code == 200
    body = resp.json()
    assert "risk_counts" in body
    assert body["risk_counts"]["stockout_risk_runs"] >= 1
    assert body["risk_counts"]["stockout_risks"] >= 1
    assert "latest_stockout_risk_run" in body
    assert body["latest_stockout_risk_run"]["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 25: Overview includes honest risk metrics only
# ---------------------------------------------------------------------------

def test_overview_has_honest_risk_metrics(override_db):
    _run_full_pipeline(api_client)
    api_client.post("/api/risks/run", json={"horizon_days": 28})

    resp = api_client.get("/api/overview")
    assert resp.status_code == 200
    body = resp.json()
    summary = body["summary"]

    # Allowed fields (real counts, not hardcoded)
    assert "critical_stockout_count" in summary
    assert "high_stockout_count" in summary
    assert "medium_stockout_count" in summary
    assert "low_stockout_count" in summary
    assert "latest_risk_run_status" in summary
    assert "latest_risk_horizon_days" in summary

    # Forbidden fields (reorder recommendations)
    assert "recommended_reorder_units" not in summary
    assert "automated_purchase_action" not in summary
    assert "supplier_negotiation_action" not in summary


# ---------------------------------------------------------------------------
# Test 26: No reorder recommendation fields introduced
# ---------------------------------------------------------------------------

def test_no_reorder_fields_in_risk_schema(in_memory_db):
    """StockoutRisk ORM must not have reorder recommendation fields."""
    forbidden = {
        "recommended_units", "reorder_quantity", "reorder_point",
        "purchase_order_action", "economic_order_qty",
    }
    risk_columns = {c.key for c in StockoutRisk.__table__.columns}
    found = forbidden & risk_columns
    assert found == set(), f"Forbidden reorder fields found in StockoutRisk: {found}"


# ---------------------------------------------------------------------------
# Test 27: Risk run is idempotent / clear-before-rewrite safe
# ---------------------------------------------------------------------------

def test_risk_run_idempotent(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=200.0)
    run_id = _insert_forecast_run(db)
    _insert_forecasts(db, run_id, days=28, p50=5.0)

    svc = StockoutService(db)
    result1 = svc.run_stockout_risk(forecast_run_id=run_id)
    result2 = svc.run_stockout_risk(forecast_run_id=run_id)

    # Both should complete
    assert result1["status"] == "completed"
    assert result2["status"] == "completed"

    # The risk run table should not have duplicate rows for the same as_of_date + mode + horizon
    # (old run should be cleared by idempotency logic)
    risk_run_count = db.query(func.count(StockoutRiskRun.id)).filter(
        StockoutRiskRun.status == "completed",
        StockoutRiskRun.mode == result1["mode"],
        StockoutRiskRun.risk_horizon_days == 28,
        StockoutRiskRun.as_of_date == result1["as_of_date"],
    ).scalar()
    assert risk_run_count == 1


# ---------------------------------------------------------------------------
# Test 28: Historical simulation mode is clearly marked
# ---------------------------------------------------------------------------

def test_historical_simulation_mode_marked(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=100.0)
    # Only a backtest run available
    run_id = _insert_forecast_run(db, mode="backtest", backtest_mode=True,
                                   test_start=date(2024, 1, 16), test_end=date(2024, 2, 12))
    _insert_forecasts(db, run_id, start_date=date(2024, 1, 16), days=28)

    svc = StockoutService(db)
    result = svc.run_stockout_risk(
        forecast_run_id=run_id,
        mode="historical_simulation",
    )

    risk_run = db.query(StockoutRiskRun).filter(
        StockoutRiskRun.id == result["risk_run_id"]
    ).first()
    assert risk_run.mode == "historical_simulation"


# ---------------------------------------------------------------------------
# Test 29: Forward planning mode returns error when no usable forecast
# ---------------------------------------------------------------------------

def test_forward_planning_errors_without_forecast(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15))
    # No forecast runs at all

    svc = StockoutService(db)
    result = svc.run_stockout_risk(mode="forward_planning")
    # Without any forecast run, should fail with clear error
    assert result["status"] == "failed"
    assert "forecast" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test 30: Existing Sprint 0–5 behavior guard
# ---------------------------------------------------------------------------

def test_forecast_run_mode_field_exists():
    """ForecastRun must have a 'mode' column (added in Sprint 6)."""
    columns = {c.key for c in ForecastRun.__table__.columns}
    assert "mode" in columns


def test_stockout_risk_run_table_exists():
    """StockoutRiskRun ORM model must be importable and have required columns."""
    required = {"id", "mode", "status", "as_of_date", "risk_horizon_days", "rows_created"}
    columns = {c.key for c in StockoutRiskRun.__table__.columns}
    missing = required - columns
    assert missing == set(), f"Missing columns in StockoutRiskRun: {missing}"


def test_stockout_risk_expanded_schema():
    """StockoutRisk must have Sprint 6 fields."""
    required = {
        "id", "risk_run_id", "as_of_date", "product_id", "store_id",
        "current_on_hand_units", "current_available_units", "inbound_units_within_horizon",
        "forecast_demand_p50", "forecast_demand_p90", "average_daily_forecast",
        "projected_end_inventory_p50", "projected_end_inventory_p90",
        "days_of_supply", "days_until_stockout", "safety_stock_units",
        "inventory_coverage_ratio", "lost_sales_units_estimate", "lost_sales_value_estimate",
        "risk_score", "risk_tier", "risk_reason",
    }
    columns = {c.key for c in StockoutRisk.__table__.columns}
    missing = required - columns
    assert missing == set(), f"Missing columns in StockoutRisk: {missing}"


def test_reorder_recommendation_table_still_empty(in_memory_db):
    """ReorderRecommendation table must remain unpopulated through Sprint 6."""
    count = in_memory_db.query(func.count(ReorderRecommendation.id)).scalar()
    assert count == 0, "ReorderRecommendation must not be populated in Sprint 6"


# ---------------------------------------------------------------------------
# Test 31: Planning forecast generates forward-looking rows
# ---------------------------------------------------------------------------

def test_planning_forecast_generates_future_rows(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=100.0)
    # Insert feature_matrix rows ending Jan 14
    _insert_feature_row(db, d=date(2024, 1, 14))

    from app.services.forecasting_service import ForecastingService
    svc = ForecastingService(db)
    result = svc.run_planning_forecast(model_type="seasonal_naive", horizon_days=14)

    assert result["status"] == "completed"
    assert result["rows_created"] > 0

    run_id = result["run_id"]
    frun = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
    assert frun.mode == "forward_planning"
    assert frun.backtest_mode is False

    # Forecast dates should be in the future (after as_of_date)
    fc_dates = [
        f.forecast_date for f in db.query(Forecast).filter(Forecast.forecast_run_id == run_id).all()
    ]
    as_of = result["as_of_date"]
    for d in fc_dates:
        assert str(d) > as_of, f"Expected future date {d} > {as_of}"


# ---------------------------------------------------------------------------
# Test 32: Forward planning runs are tagged correctly
# ---------------------------------------------------------------------------

def test_forward_planning_run_tagged(in_memory_db):
    db = in_memory_db
    _insert_supplier(db); _insert_product(db); _insert_store(db)
    _insert_inventory(db, d=date(2024, 1, 15), on_hand=100.0)
    _insert_feature_row(db, d=date(2024, 1, 14))

    from app.services.forecasting_service import ForecastingService
    svc = ForecastingService(db)
    result = svc.run_planning_forecast(model_type="moving_average_7d", horizon_days=7)

    run_id = result["run_id"]
    frun = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()

    assert frun.mode == "forward_planning"
    assert frun.backtest_mode is False
    assert frun.status == "completed"
    assert frun.rows_created > 0
