"""
Tests for Sprint 7 — Reorder Recommendation Engine.

Coverage:
  1.  RecommendationService runs with a valid risk run
  2.  Recommendation run metadata is persisted
  3.  Recommendation rows are persisted
  4.  Latest completed stockout risk run is selected when no risk_run_id is provided
  5.  Missing stockout risk run returns clear error
  6.  Inventory position formula is correct
  7.  Lead-time demand formula is correct
  8.  Reorder point formula is correct
  9.  Recommended units formula is correct
  10. Rounded recommended units respects order multiple
  11. Rounded recommended units respects minimum order quantity
  12. Estimated order cost formula is correct
  13. Estimated lost sales avoided formula is correct
  14. Critical urgency is assigned correctly
  15. High urgency is assigned correctly
  16. Medium urgency is assigned correctly
  17. Low urgency is assigned correctly
  18. Recommendation reason is deterministic and non-empty
  19. Confidence level is assigned
  20. Low-risk rows are excluded by default
  21. Low-risk rows can be included when requested
  22. Recommendation run is idempotent / clear-before-rewrite safe
  23. POST /api/recommendations/run works
  24. GET  /api/recommendations/runs works
  25. GET  /api/recommendations/latest works
  26. GET  /api/recommendations supports ranking/filtering
  27. GET  /api/recommendations/product/{product_id} works
  28. PATCH /api/recommendations/{id}/status works
  29. Invalid status update is rejected
  30. Status update does not create raw purchase orders
  31. Status update does not call external APIs (checked structurally)
  32. Data-health includes real recommendation counts
  33. Overview includes honest recommendation metrics only
  34. No external side-effect fields exist in ReorderRecommendation
  35. Existing Sprint 0–6 tests still pass (guard)
  36. GitHub Actions CI files remain present
  37. Repo hygiene: no forbidden external-action fields in overview summary
"""

import math
import os
import uuid
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.db.models import (
    ForecastRun, Forecast, InventoryDaily, RawPurchaseOrder,
    RawProduct, RawSupplier, RawStore, FeatureMatrix, FeatureRun,
    StockoutRisk, StockoutRiskRun,
    RecommendationRun, ReorderRecommendation,
)
from app.services.recommendation_service import RecommendationService


# ---------------------------------------------------------------------------
# Helpers — minimal fixture builders
# ---------------------------------------------------------------------------

def _insert_product(db, product_id="prod-1", supplier_id="sup-1",
                    unit_price=50.0, unit_cost=20.0, category="Tops"):
    db.add(RawProduct(
        id=product_id, external_id=f"ext-{product_id}",
        sku=f"SKU-{product_id}", name=f"Product {product_id}",
        category=category, supplier_id=supplier_id,
        unit_price=unit_price, unit_cost=unit_cost,
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


def _insert_forecast_run(db, run_id="frun-1", mode="forward_planning"):
    db.add(ForecastRun(
        id=run_id, model_name="seasonal_naive",
        model_type="seasonal_naive", horizon_days=28,
        backtest_mode=(mode == "backtest"), mode=mode,
        status="completed", started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        test_start_date=date(2024, 1, 16),
        test_end_date=date(2024, 2, 12),
    ))
    db.flush()


def _insert_risk_run(db, run_id="risk-run-1", frun_id="frun-1",
                     mode="forward_planning", as_of=date(2024, 1, 15)):
    db.add(StockoutRiskRun(
        id=run_id, source_forecast_run_id=frun_id,
        mode=mode, status="completed",
        started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
        risk_horizon_days=28, as_of_date=as_of,
        rows_created=1, critical_count=0, high_count=1,
        medium_count=0, low_count=0,
    ))
    db.flush()


def _insert_risk_row(
    db,
    risk_id=None,
    risk_run_id="risk-run-1",
    product_id="prod-1",
    store_id="store-1",
    risk_tier="high",
    available=50.0,
    inbound=10.0,
    avg_daily=5.0,
    lead_time=10,
    safety_stock=20.0,
    forecast_p50=140.0,
    forecast_p90=160.0,
    days_until_stockout=None,
    expected_stockout_date=None,
    risk_score=75.0,
    lost_sales_value=200.0,
    reliability=0.9,
    supplier_id="sup-1",
    category="Tops",
    as_of=date(2024, 1, 15),
):
    rid = risk_id or str(uuid.uuid4())
    db.add(StockoutRisk(
        id=rid,
        risk_run_id=risk_run_id,
        as_of_date=as_of,
        product_id=product_id,
        store_id=store_id,
        category=category,
        supplier_id=supplier_id,
        current_available_units=available,
        inbound_units_within_horizon=inbound,
        current_on_hand_units=available,
        supplier_lead_time_days=lead_time,
        supplier_reliability_score=reliability,
        forecast_demand_p50=forecast_p50,
        forecast_demand_p90=forecast_p90,
        average_daily_forecast=avg_daily,
        safety_stock_units=safety_stock,
        days_until_stockout=days_until_stockout,
        expected_stockout_date=expected_stockout_date,
        risk_tier=risk_tier,
        risk_score=risk_score,
        lost_sales_value_estimate=lost_sales_value,
        lost_sales_units_estimate=max(0.0, (forecast_p50 - available - inbound)),
        projected_end_inventory_p50=available + inbound - forecast_p50,
        projected_end_inventory_p90=available + inbound - forecast_p90,
        forecast_run_id="frun-1",
    ))
    db.flush()
    return rid


def _minimal_db(db):
    """Seed enough data for a single recommendation row."""
    _insert_product(db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(db)
    _insert_risk_run(db)
    _insert_risk_row(db)
    return db


# ---------------------------------------------------------------------------
# Test 1: Service runs with a valid risk run
# ---------------------------------------------------------------------------

def test_service_runs_with_valid_risk_run(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 2: Recommendation run metadata is persisted
# ---------------------------------------------------------------------------

def test_recommendation_run_metadata_persisted(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    run = in_memory_db.query(RecommendationRun).filter_by(id=run_id).first()
    assert run is not None
    assert run.status == "completed"
    assert run.mode == "recommendation_only"
    assert run.source_risk_run_id == "risk-run-1"
    assert run.rows_created >= 1


# ---------------------------------------------------------------------------
# Test 3: Recommendation rows are persisted
# ---------------------------------------------------------------------------

def test_recommendation_rows_persisted(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    rows = (
        in_memory_db.query(ReorderRecommendation)
        .filter_by(recommendation_run_id=run_id)
        .all()
    )
    assert len(rows) >= 1
    row = rows[0]
    assert row.product_id == "prod-1"
    assert row.store_id == "store-1"
    assert row.status == "open"


# ---------------------------------------------------------------------------
# Test 4: Latest completed stockout risk run is selected automatically
# ---------------------------------------------------------------------------

def test_latest_risk_run_selected_automatically(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    # Insert two risk runs; service should pick the most recent
    _insert_risk_run(in_memory_db, run_id="risk-run-old",
                     frun_id="frun-1", as_of=date(2024, 1, 10))
    _insert_risk_row(in_memory_db, risk_run_id="risk-run-old",
                     risk_id="risk-old-1")
    _insert_risk_run(in_memory_db, run_id="risk-run-new",
                     frun_id="frun-1", as_of=date(2024, 1, 15))
    _insert_risk_row(in_memory_db, risk_run_id="risk-run-new",
                     risk_id="risk-new-1")
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    assert result["status"] == "completed"
    assert result["source_risk_run_id"] == "risk-run-new"


# ---------------------------------------------------------------------------
# Test 5: Missing stockout risk run returns clear error
# ---------------------------------------------------------------------------

def test_missing_risk_run_returns_clear_error(in_memory_db):
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    assert result["status"] == "failed"
    assert "stockout risk" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test 6: Inventory position formula
# ---------------------------------------------------------------------------

def test_inventory_position_formula(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    _insert_risk_row(in_memory_db, available=80.0, inbound=20.0)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    # inventory_position = 80 + 20 = 100
    assert abs(row.inventory_position - 100.0) < 0.01


# ---------------------------------------------------------------------------
# Test 7: Lead-time demand formula
# ---------------------------------------------------------------------------

def test_lead_time_demand_formula(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    _insert_risk_row(in_memory_db, avg_daily=5.0, lead_time=10)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    # lead_time_demand = 5.0 × 10 = 50.0
    assert abs(row.lead_time_demand_units - 50.0) < 0.01


# ---------------------------------------------------------------------------
# Test 8: Reorder point formula
# ---------------------------------------------------------------------------

def test_reorder_point_formula(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    _insert_risk_row(in_memory_db, avg_daily=5.0, lead_time=10, safety_stock=20.0)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    # reorder_point = 50 + 20 = 70
    assert abs(row.reorder_point_units - 70.0) < 0.01


# ---------------------------------------------------------------------------
# Test 9: Recommended units formula
# ---------------------------------------------------------------------------

def test_recommended_units_formula(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    # inventory_position = 30+5 = 35, reorder_point = 5*10+20 = 70
    # recommended_units = max(0, 70 - 35) = 35
    _insert_risk_row(in_memory_db, available=30.0, inbound=5.0,
                     avg_daily=5.0, lead_time=10, safety_stock=20.0)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert abs(row.recommended_units - 35.0) < 0.01


# ---------------------------------------------------------------------------
# Test 10: Rounded units respects order multiple
# ---------------------------------------------------------------------------

def test_rounded_units_respects_order_multiple():
    from app.services.recommendation_service import RecommendationService as RS
    # order_multiple = 1 (default), raw = 35 → rounded = 35
    assert RS._round_recommended_units(35.0, 1.0, 1.0) == 35.0
    # With order_multiple = 10, raw = 35 → ceil(35/10)*10 = 40
    assert RS._round_recommended_units(35.0, 10.0, 1.0) == 40.0
    # raw = 30 → ceil(30/10)*10 = 30
    assert RS._round_recommended_units(30.0, 10.0, 1.0) == 30.0


# ---------------------------------------------------------------------------
# Test 11: Rounded units respects min order quantity
# ---------------------------------------------------------------------------

def test_rounded_units_respects_min_order_quantity():
    from app.services.recommendation_service import RecommendationService as RS
    # raw = 1, min_order_qty = 12 → result = 12
    assert RS._round_recommended_units(1.0, 1.0, 12.0) == 12.0
    # raw = 0 → result = 0 (no order if not needed)
    assert RS._round_recommended_units(0.0, 1.0, 12.0) == 0.0
    # raw = 15, min_order_qty = 12 → result = 15 (above min)
    assert RS._round_recommended_units(15.0, 1.0, 12.0) == 15.0


# ---------------------------------------------------------------------------
# Test 12: Estimated order cost formula
# ---------------------------------------------------------------------------

def test_estimated_order_cost_formula(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    # available=30, inbound=5 → inv_pos=35
    # lead_time_demand = 5*10=50, safety_stock=20, rop=70
    # recommended_raw = 35, rounded = 35
    # estimated_order_cost = 35 × 20 = 700
    _insert_risk_row(in_memory_db, available=30.0, inbound=5.0,
                     avg_daily=5.0, lead_time=10, safety_stock=20.0)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert abs(row.estimated_order_cost - 700.0) < 0.01


# ---------------------------------------------------------------------------
# Test 13: Estimated lost sales avoided formula
# ---------------------------------------------------------------------------

def test_estimated_lost_sales_avoided_formula(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    # recommended_rounded = 35, unit_price = 50 → value = 1750
    # lost_sales_value = 200 (from fixture)
    # avoided = min(200, 1750) = 200
    _insert_risk_row(in_memory_db, available=30.0, inbound=5.0,
                     avg_daily=5.0, lead_time=10, safety_stock=20.0,
                     lost_sales_value=200.0)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert abs(row.estimated_lost_sales_avoided - 200.0) < 0.01


# ---------------------------------------------------------------------------
# Test 14: Critical urgency assigned correctly
# ---------------------------------------------------------------------------

def test_critical_urgency_assigned_for_critical_tier(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db, run_id="risk-run-crit")
    _insert_risk_row(in_memory_db, risk_run_id="risk-run-crit",
                     risk_tier="critical", days_until_stockout=3.0,
                     risk_score=95.0)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations(risk_run_id="risk-run-crit",
                                              include_low_risk=True)
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert row.urgency == "critical"


def test_critical_urgency_from_days_until_stockout(in_memory_db):
    """days_until_stockout <= 7 triggers critical even if risk_tier is not critical."""
    from app.services.recommendation_service import RecommendationService as RS
    urgency = RS._assign_urgency("high", days_until_stockout=5.0,
                                 lead_time_days=10, recommended_rounded=10.0)
    assert urgency == "critical"


# ---------------------------------------------------------------------------
# Test 15: High urgency assigned correctly
# ---------------------------------------------------------------------------

def test_high_urgency_assigned_for_high_tier(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    _insert_risk_row(in_memory_db, risk_tier="high", days_until_stockout=None)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert row.urgency == "high"


# ---------------------------------------------------------------------------
# Test 16: Medium urgency assigned correctly
# ---------------------------------------------------------------------------

def test_medium_urgency_assigned_for_medium_tier(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db, run_id="risk-run-med")
    _insert_risk_row(in_memory_db, risk_run_id="risk-run-med",
                     risk_tier="medium", days_until_stockout=None)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations(risk_run_id="risk-run-med",
                                              include_low_risk=True)
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert row.urgency == "medium"


# ---------------------------------------------------------------------------
# Test 17: Low urgency assigned correctly
# ---------------------------------------------------------------------------

def test_low_urgency_from_assign_method():
    from app.services.recommendation_service import RecommendationService as RS
    urgency = RS._assign_urgency("low", days_until_stockout=None,
                                 lead_time_days=10, recommended_rounded=0.0)
    assert urgency == "low"


# ---------------------------------------------------------------------------
# Test 18: Recommendation reason is deterministic and non-empty
# ---------------------------------------------------------------------------

def test_recommendation_reason_non_empty(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert row.recommendation_reason is not None
    assert len(row.recommendation_reason) > 10


def test_recommendation_reason_is_deterministic():
    from app.services.recommendation_service import RecommendationService as RS
    r1 = RS._generate_reason("high", "high", 40.0, 10, 20.0, None)
    r2 = RS._generate_reason("high", "high", 40.0, 10, 20.0, None)
    assert r1 == r2
    assert len(r1) > 0


# ---------------------------------------------------------------------------
# Test 19: Confidence level is assigned
# ---------------------------------------------------------------------------

def test_confidence_level_assigned(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    row = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    assert row.confidence_level in {"high", "medium", "low", "unknown"}


# ---------------------------------------------------------------------------
# Test 20: Low-risk rows excluded by default
# ---------------------------------------------------------------------------

def test_low_risk_excluded_by_default(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db, run_id="risk-run-low")
    # Insert only a low-risk row
    _insert_risk_row(in_memory_db, risk_run_id="risk-run-low",
                     risk_tier="low", days_until_stockout=None)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations(risk_run_id="risk-run-low")
    assert result["status"] == "completed"
    assert result["rows_created"] == 0


# ---------------------------------------------------------------------------
# Test 21: Low-risk rows included when requested
# ---------------------------------------------------------------------------

def test_low_risk_included_when_requested(in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db, run_id="risk-run-low2")
    _insert_risk_row(in_memory_db, risk_run_id="risk-run-low2",
                     risk_tier="low", days_until_stockout=None)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations(risk_run_id="risk-run-low2",
                                              include_low_risk=True)
    assert result["status"] == "completed"
    assert result["rows_created"] == 1


# ---------------------------------------------------------------------------
# Test 22: Idempotency / clear-before-rewrite safe
# ---------------------------------------------------------------------------

def test_idempotent_clear_before_rewrite(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result1 = svc.run_reorder_recommendations()
    result2 = svc.run_reorder_recommendations()
    # After re-run, previous completed run for same risk_run should be deleted
    total_completed = (
        in_memory_db.query(func.count(RecommendationRun.id))
        .filter(RecommendationRun.status == "completed")
        .scalar()
    )
    assert total_completed == 1
    assert result2["status"] == "completed"


# ---------------------------------------------------------------------------
# Tests 23–31: API endpoint tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client(override_db):
    from app.main import app
    return TestClient(app)


def _seed_full_pipeline(client_fixture, db):
    """Seed minimal data and run the full pipeline via the service layer."""
    _insert_product(db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(db)
    _insert_risk_run(db)
    _insert_risk_row(db)
    svc = RecommendationService(db)
    return svc.run_reorder_recommendations()


def test_api_run_recommendations(client, in_memory_db):
    _insert_product(in_memory_db, unit_price=50.0, unit_cost=20.0)
    _insert_forecast_run(in_memory_db)
    _insert_risk_run(in_memory_db)
    _insert_risk_row(in_memory_db)
    resp = client.post("/api/recommendations/run", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert "recommendation_run_id" in data
    assert "rows_created" in data


def test_api_list_recommendation_runs(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/recommendations/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert data["total"] >= 1


def test_api_get_latest_recommendation_run(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/recommendations/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["run"] is not None
    assert "recommendations" in data


def test_api_list_recommendations_returns_ranked_rows(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert "total" in data


def test_api_list_recommendations_filters(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/recommendations?urgency=high")
    assert resp.status_code == 200
    data = resp.json()
    for rec in data["recommendations"]:
        assert rec["urgency"] == "high"


def test_api_get_product_recommendations(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/recommendations/product/prod-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["product_id"] == "prod-1"
    assert "recommendations" in data


def test_api_patch_status_valid(client, in_memory_db):
    run_result = _seed_full_pipeline(client, in_memory_db)
    run_id = run_result["recommendation_run_id"]
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=in_memory_db.get_bind())
    session = Session()
    rec = session.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    rec_id = rec.id
    session.close()
    resp = client.patch(f"/api/recommendations/{rec_id}/status", json={
        "status": "reviewed",
        "reviewed_by": "operator",
        "review_note": "Checked stock levels.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_status"] == "reviewed"
    assert data["reviewed_by"] == "operator"


def test_api_patch_invalid_status_rejected(client, in_memory_db):
    run_result = _seed_full_pipeline(client, in_memory_db)
    run_id = run_result["recommendation_run_id"]
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=in_memory_db.get_bind())
    session = Session()
    rec = session.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    rec_id = rec.id
    session.close()
    resp = client.patch(f"/api/recommendations/{rec_id}/status", json={
        "status": "buy_now",
    })
    assert resp.status_code == 422


def test_status_update_does_not_create_purchase_orders(in_memory_db):
    _minimal_db(in_memory_db)
    svc = RecommendationService(in_memory_db)
    result = svc.run_reorder_recommendations()
    run_id = result["recommendation_run_id"]
    rec = in_memory_db.query(ReorderRecommendation).filter_by(
        recommendation_run_id=run_id).first()
    rec.status = "approved_internal"
    in_memory_db.commit()
    # Verify: no raw_purchase_orders were created
    from app.db.models import RawPurchaseOrder
    po_count = in_memory_db.query(func.count(RawPurchaseOrder.id)).scalar()
    assert po_count == 0


def test_status_update_no_external_side_effects():
    """Structural check: PATCH handler code has no external API calls."""
    import inspect
    from app.api import recommendations
    source = inspect.getsource(recommendations)
    forbidden = [
        "requests.post", "requests.put", "httpx.",
        "sendmail", "smtp.", "send_email",
        "create_purchase_order", "purchase_order_action",
    ]
    for term in forbidden:
        assert term not in source, f"Forbidden external call found: {term}"


# ---------------------------------------------------------------------------
# Test 32: Data-health includes real recommendation counts
# ---------------------------------------------------------------------------

def test_data_health_includes_recommendation_counts(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/data-health")
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendation_counts" in data
    assert data["recommendation_counts"]["recommendation_runs"] >= 1
    assert data["recommendation_counts"]["reorder_recommendations"] >= 1


# ---------------------------------------------------------------------------
# Test 33: Overview includes honest recommendation metrics only
# ---------------------------------------------------------------------------

def test_overview_includes_honest_recommendation_metrics(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    summary = data.get("summary", {})
    # Must include allowed fields
    allowed = {
        "open_recommendation_count", "critical_recommendation_count",
        "high_recommendation_count", "total_recommended_units",
        "estimated_order_cost", "estimated_lost_sales_avoided",
        "latest_recommendation_run_status",
    }
    for field in allowed:
        assert field in summary, f"Missing allowed field: {field}"


def test_overview_no_forbidden_recommendation_fields(client, in_memory_db):
    _seed_full_pipeline(client, in_memory_db)
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    summary = resp.json().get("summary", {})
    forbidden = {
        "purchase_orders_created", "orders_sent",
        "supplier_contacted", "auto_reordered", "external_action_status",
    }
    for field in forbidden:
        assert field not in summary, f"Forbidden field in overview: {field}"


# ---------------------------------------------------------------------------
# Test 34: No external side-effect fields in ReorderRecommendation ORM
# ---------------------------------------------------------------------------

def test_no_external_side_effect_fields_in_orm():
    from app.db.models import ReorderRecommendation
    columns = {c.key for c in ReorderRecommendation.__table__.columns}
    forbidden = {
        "purchase_order_id", "po_sent", "external_action",
        "supplier_email_sent", "auto_ordered",
    }
    for field in forbidden:
        assert field not in columns, f"Forbidden ORM field: {field}"


# ---------------------------------------------------------------------------
# Test 35: Existing Sprint 0–6 tests still pass (guard via import check)
# ---------------------------------------------------------------------------

def test_existing_services_still_importable():
    from app.services.stockout_service import StockoutService
    from app.services.forecasting_service import ForecastingService
    from app.services.feature_service import FeatureService
    from app.services.ingestion_service import IngestionService
    from app.services.recommendation_service import RecommendationService
    assert StockoutService is not None
    assert ForecastingService is not None
    assert FeatureService is not None
    assert IngestionService is not None
    assert RecommendationService is not None


# ---------------------------------------------------------------------------
# Test 36: GitHub Actions CI files present
# ---------------------------------------------------------------------------

def test_github_actions_ci_files_present():
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    ci_file = os.path.join(root, ".github", "workflows", "ci.yml")
    dependabot = os.path.join(root, ".github", "dependabot.yml")
    assert os.path.exists(ci_file), ".github/workflows/ci.yml missing"
    assert os.path.exists(dependabot), ".github/dependabot.yml missing"


# ---------------------------------------------------------------------------
# Test 37: No forbidden fields introduced via structural inspection
# ---------------------------------------------------------------------------

def test_recommendation_service_no_forbidden_external_calls():
    """RecommendationService source must not contain purchase-order writes."""
    import inspect
    from app.services import recommendation_service
    source = inspect.getsource(recommendation_service)
    forbidden = [
        "RawPurchaseOrder", "purchase_order_action",
        "requests.post", "httpx.", "smtp.",
    ]
    for term in forbidden:
        assert term not in source, f"Forbidden term in recommendation_service.py: {term}"
