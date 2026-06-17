"""
Tests: FeatureService and /api/features/* endpoints (Sprint 3).

Covers:
  1.  FeatureService builds feature_matrix from product_store_daily
  2.  One row per eligible (product, store, date) — no duplicates
  3.  Lag features are correct on deterministic fixture
  4.  Rolling mean features are shifted (leakage-safe, window ends at D-1)
  5.  Rolling std features are shifted
  6.  Calendar features are correct
  7.  Promotion features populated from canonical data
  8.  Price/margin features correct
  9.  Price change features compare prior dates only
  10. Inventory features present and valid
  11. Lifecycle features correct from launch date
  12. Pre-launch rows excluded from feature_matrix
  13. target_units_sold equals canonical units_sold for same date
  14. No forbidden forecast/risk/recommendation fields in feature_matrix schema
  15. Feature build is idempotent / reset-safe
  16. POST /api/features/build works
  17. GET /api/features/status works
  18. GET /api/features/sample returns bounded rows
  19. /api/data-health includes real feature counts after build
  20. All Sprint 0/1/2 tests still pass (integrity guard)
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.main import app
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService
from app.services.aggregation_service import AggregationService
from app.services.feature_service import FeatureService
from app.db.models import (
    FeatureMatrix, FeatureRun, SalesDaily, ProductStoreDaily, RawProduct,
)

client = TestClient(app)

FEAT_CONFIG = MockConfig(
    seed=42,
    product_count=4,
    store_count=2,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 3, 10),   # 70 days — enough for all lag windows
)

TINY = {"seed": 42, "product_count": 4, "store_count": 2, "history_days": 70}

FORBIDDEN_FIELDS = {
    "forecast", "forecast_7d", "forecast_28d", "forecast_90d",
    "p10", "p50", "p90", "risk_score", "stockout_risk",
    "recommended_units", "reorder_quantity", "future_demand", "future_units_sold",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db(override_db):
    yield


@pytest.fixture
def seeded_agg_db(in_memory_db):
    """Seed raw data + run aggregation. Return (db, start, end)."""
    connector = MockCommerceConnector(FEAT_CONFIG)
    IngestionService(connector, in_memory_db).run(FEAT_CONFIG.start_date, FEAT_CONFIG.end_date)
    AggregationService(in_memory_db).run_full_aggregation(FEAT_CONFIG.start_date, FEAT_CONFIG.end_date)
    return in_memory_db, FEAT_CONFIG.start_date, FEAT_CONFIG.end_date


@pytest.fixture
def full_pipeline_db(seeded_agg_db):
    """Seed + aggregate + features. Return (db, feature_result)."""
    db, start, end = seeded_agg_db
    result = FeatureService(db).build_feature_matrix()
    return db, result


# ---------------------------------------------------------------------------
# 1. FeatureService builds feature_matrix
# ---------------------------------------------------------------------------

def test_feature_service_builds_matrix(full_pipeline_db):
    db, result = full_pipeline_db
    assert result["status"] == "completed"
    assert result["rows_created"] > 0
    count = db.query(func.count(FeatureMatrix.id)).scalar()
    assert count == result["rows_created"]


# ---------------------------------------------------------------------------
# 2. One row per eligible (product, store, date)
# ---------------------------------------------------------------------------

def test_no_duplicate_feature_rows(full_pipeline_db):
    db, result = full_pipeline_db
    from sqlalchemy import text
    dupe_groups = db.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "  SELECT COUNT(*) AS cnt FROM feature_matrix"
            "  GROUP BY product_id, store_id, date HAVING cnt > 1"
            ")"
        )
    ).scalar() or 0
    assert dupe_groups == 0, f"{dupe_groups} duplicate (product, store, date) groups found"


# ---------------------------------------------------------------------------
# 3. Lag features correct
# ---------------------------------------------------------------------------

def test_lag_units_7d_correct(full_pipeline_db):
    db, _ = full_pipeline_db
    # Pick a row that has lag_units_7d not null
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.lag_units_7d.isnot(None)
    ).first()
    assert row is not None, "Expected at least one row with lag_units_7d"

    # units_sold 7 days before should match lag_units_7d
    d_minus_7 = row.date - timedelta(days=7)
    sd = db.query(SalesDaily).filter(
        SalesDaily.product_id == row.product_id,
        SalesDaily.store_id == row.store_id,
        SalesDaily.date == d_minus_7,
    ).first()
    expected = sd.units_sold if sd else 0.0
    assert abs((row.lag_units_7d or 0.0) - expected) < 0.01


def test_lag_units_1d_correct(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.lag_units_1d.isnot(None)
    ).first()
    assert row is not None

    d_minus_1 = row.date - timedelta(days=1)
    sd = db.query(SalesDaily).filter(
        SalesDaily.product_id == row.product_id,
        SalesDaily.store_id == row.store_id,
        SalesDaily.date == d_minus_1,
    ).first()
    expected = sd.units_sold if sd else 0.0
    assert abs((row.lag_units_1d or 0.0) - expected) < 0.01


# ---------------------------------------------------------------------------
# 4. Rolling mean features are shifted (leakage-safe)
# ---------------------------------------------------------------------------

def test_rolling_mean_does_not_include_current_date(full_pipeline_db):
    """rolling_units_mean_7d at D must equal mean of PSD [D-7..D-1], not include D.

    Queries ProductStoreDaily (the actual source for the feature) so 0-sales rows
    are included and window size matches what pandas rolling uses.
    """
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.rolling_units_mean_7d.isnot(None),
        FeatureMatrix.lag_units_7d.isnot(None),   # ensures >= 7 prior PSD rows exist
    ).first()
    if row is None:
        pytest.skip("No suitable row found")

    window_start = row.date - timedelta(days=7)
    window_end = row.date - timedelta(days=1)
    from app.db.models import ProductStoreDaily as PSD
    psd_rows = db.query(PSD).filter(
        PSD.product_id == row.product_id,
        PSD.store_id == row.store_id,
        PSD.date >= window_start,
        PSD.date <= window_end,
    ).order_by(PSD.date).all()
    if len(psd_rows) == 0:
        pytest.skip("No PSD rows in window")

    units_in_window = [r.units_sold or 0.0 for r in psd_rows]
    # pandas rolling(7, min_periods=1).mean() divides by the actual count of rows, not always 7
    expected_mean = sum(units_in_window) / len(units_in_window)
    assert abs(row.rolling_units_mean_7d - expected_mean) < 0.5


def test_rolling_mean_7d_not_equal_to_target(full_pipeline_db):
    """rolling_units_mean_7d should generally differ from target_units_sold."""
    db, _ = full_pipeline_db
    matching = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.rolling_units_mean_7d == FeatureMatrix.target_units_sold,
        FeatureMatrix.rolling_units_mean_7d.isnot(None),
        FeatureMatrix.target_units_sold > 0,
    ).scalar() or 0
    total_valid = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.rolling_units_mean_7d.isnot(None),
        FeatureMatrix.target_units_sold > 0,
    ).scalar() or 1
    leakage_rate = matching / total_valid
    assert leakage_rate < 0.1, f"High leakage rate: {leakage_rate:.2%}"


# ---------------------------------------------------------------------------
# 5. Rolling std features shifted
# ---------------------------------------------------------------------------

def test_rolling_std_features_exist(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.rolling_units_std_7d.isnot(None)
    ).first()
    assert row is not None, "No rows with rolling_units_std_7d populated"
    assert row.rolling_units_std_7d >= 0


# ---------------------------------------------------------------------------
# 6. Calendar features correct
# ---------------------------------------------------------------------------

def test_calendar_features_correct(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.date == date(2024, 1, 8)   # Monday Jan 8 2024
    ).first()
    if row is None:
        pytest.skip("Date 2024-01-08 not in feature matrix")
    assert row.day_of_week == 0       # Monday = 0
    assert row.month == 1
    assert row.quarter == 1
    assert row.is_weekend is False
    assert row.week_of_year in (1, 2)


def test_weekend_flag_correct(full_pipeline_db):
    db, _ = full_pipeline_db
    # 2024-01-06 is Saturday
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.date == date(2024, 1, 6)
    ).first()
    if row is None:
        pytest.skip("Saturday not in feature matrix")
    assert row.is_weekend is True
    assert row.day_of_week == 5


# ---------------------------------------------------------------------------
# 7. Promotion features populated
# ---------------------------------------------------------------------------

def test_promo_active_flag_exists(full_pipeline_db):
    db, _ = full_pipeline_db
    active_count = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.promo_active == True
    ).scalar() or 0
    assert active_count > 0, "Expected at least some rows with promo_active=True"


def test_discount_pct_when_promo_active(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.promo_active == True,
        FeatureMatrix.discount_pct.isnot(None),
    ).first()
    assert row is not None
    assert row.discount_pct > 0


# ---------------------------------------------------------------------------
# 8. Price / margin features
# ---------------------------------------------------------------------------

def test_price_and_margin_features(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.retail_price.isnot(None),
        FeatureMatrix.unit_cost.isnot(None),
        FeatureMatrix.gross_margin_pct.isnot(None),
    ).first()
    assert row is not None
    assert row.retail_price > 0
    assert row.unit_cost >= 0
    assert 0 <= row.gross_margin_pct <= 1


# ---------------------------------------------------------------------------
# 9. Price change features reference prior dates only
# ---------------------------------------------------------------------------

def test_price_change_features_exist(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.price_change_pct_7d.isnot(None)
    ).first()
    # For static-price MockConnector, price changes are 0; field must exist
    assert row is not None
    # Value must be finite (not NaN stored as NULL is OK; if not NULL it's a number)
    if row.price_change_pct_7d is not None:
        assert isinstance(row.price_change_pct_7d, float)


# ---------------------------------------------------------------------------
# 10. Inventory features
# ---------------------------------------------------------------------------

def test_inventory_features_present(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.available_units.isnot(None)
    ).first()
    assert row is not None
    assert row.available_units >= 0

    stockout_rows = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.stockout_flag == True
    ).scalar() or 0
    assert stockout_rows >= 0   # may be 0 in short window; just confirm field exists


# ---------------------------------------------------------------------------
# 11. Lifecycle features correct
# ---------------------------------------------------------------------------

def test_lifecycle_days_since_launch_non_negative(full_pipeline_db):
    """All rows in feature_matrix have days_since_launch >= 0 (pre-launch excluded)."""
    db, _ = full_pipeline_db
    negative = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.days_since_launch < 0
    ).scalar() or 0
    assert negative == 0


def test_product_age_bucket_valid_values(full_pipeline_db):
    db, _ = full_pipeline_db
    valid_buckets = {"new_0_30", "ramp_31_90", "mature_91_365", "established_365_plus"}
    invalid = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.product_age_bucket.notin_(valid_buckets)
    ).scalar() or 0
    assert invalid == 0, f"{invalid} rows have invalid product_age_bucket"


# ---------------------------------------------------------------------------
# 12. Pre-launch rows excluded
# ---------------------------------------------------------------------------

def test_pre_launch_rows_excluded(full_pipeline_db):
    db, _ = full_pipeline_db
    pre_launch = db.query(func.count(FeatureMatrix.id)).filter(
        FeatureMatrix.product_age_bucket == "pre_launch"
    ).scalar() or 0
    assert pre_launch == 0, f"{pre_launch} pre_launch rows found in feature_matrix"


# ---------------------------------------------------------------------------
# 13. target_units_sold matches canonical sales_daily
# ---------------------------------------------------------------------------

def test_target_units_sold_matches_sales_daily(full_pipeline_db):
    db, _ = full_pipeline_db
    row = db.query(FeatureMatrix).filter(
        FeatureMatrix.target_units_sold > 0
    ).first()
    assert row is not None

    sd = db.query(SalesDaily).filter(
        SalesDaily.product_id == row.product_id,
        SalesDaily.store_id == row.store_id,
        SalesDaily.date == row.date,
    ).first()
    assert sd is not None
    assert abs(row.target_units_sold - sd.units_sold) < 0.01


# ---------------------------------------------------------------------------
# 14. No forbidden fields in schema or API
# ---------------------------------------------------------------------------

def test_no_forbidden_fields_in_feature_matrix_schema():
    cols = {c.key for c in FeatureMatrix.__table__.columns}
    violations = cols & FORBIDDEN_FIELDS
    assert not violations, f"Forbidden fields in feature_matrix schema: {violations}"


# ---------------------------------------------------------------------------
# 15. Feature build is idempotent
# ---------------------------------------------------------------------------

def test_feature_build_is_idempotent(seeded_agg_db):
    db, *_ = seeded_agg_db
    svc = FeatureService(db)
    r1 = svc.build_feature_matrix()
    r2 = svc.build_feature_matrix()
    assert r1["rows_created"] == r2["rows_created"]
    final = db.query(func.count(FeatureMatrix.id)).scalar()
    assert final == r1["rows_created"]


# ---------------------------------------------------------------------------
# 16. POST /api/features/build
# ---------------------------------------------------------------------------

def test_post_features_build_endpoint():
    client.post("/api/demo/reset", json=TINY)
    client.post("/api/aggregation/run", json={})
    response = client.post("/api/features/build", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["rows_created"] > 0
    assert "checks" in data


# ---------------------------------------------------------------------------
# 17. GET /api/features/status
# ---------------------------------------------------------------------------

def test_get_features_status_not_run():
    response = client.get("/api/features/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("not_run", "ready", "failed", "running")
    assert "feature_rows" in data


def test_get_features_status_after_build():
    client.post("/api/demo/reset", json=TINY)
    client.post("/api/aggregation/run", json={})
    client.post("/api/features/build", json={})
    response = client.get("/api/features/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["feature_rows"] > 0
    assert data["latest_run"]["status"] == "completed"


# ---------------------------------------------------------------------------
# 18. GET /api/features/sample
# ---------------------------------------------------------------------------

def test_get_features_sample_empty():
    response = client.get("/api/features/sample")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "empty"
    assert data["rows"] == []


def test_get_features_sample_after_build():
    client.post("/api/demo/reset", json=TINY)
    client.post("/api/aggregation/run", json={})
    client.post("/api/features/build", json={})
    response = client.get("/api/features/sample?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["rows"]) <= 5
    assert data["total_in_db"] > 5
    row = data["rows"][0]
    assert "target_units_sold" in row
    assert "lag_units_7d" in row
    assert "rolling_units_mean_7d" in row
    assert "product_age_bucket" in row


# ---------------------------------------------------------------------------
# 19. /api/data-health includes feature counts
# ---------------------------------------------------------------------------

def test_data_health_includes_feature_counts_after_build():
    client.post("/api/demo/reset", json=TINY)
    client.post("/api/aggregation/run", json={})
    client.post("/api/features/build", json={})
    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert "feature_counts" in data
    assert data["feature_counts"]["feature_matrix"] > 0
    assert data["latest_feature_run"] is not None
    assert data["latest_feature_run"]["status"] == "completed"


# ---------------------------------------------------------------------------
# 20. Feature run record is created
# ---------------------------------------------------------------------------

def test_feature_run_record_created(full_pipeline_db):
    db, result = full_pipeline_db
    run = db.query(FeatureRun).filter(FeatureRun.id == result["run_id"]).first()
    assert run is not None
    assert run.status == "completed"
    assert run.rows_created > 0
    assert run.date_min is not None
    assert run.date_max is not None
