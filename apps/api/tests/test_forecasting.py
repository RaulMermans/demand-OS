"""
Tests: ForecastingService and /api/forecasts/* endpoints (Sprint 4).

Covers:
  1.  ForecastingService runs seasonal_naive baseline
  2.  ForecastingService runs moving_average_7d baseline
  3.  ForecastingService runs moving_average_28d baseline
  4.  Seasonal naive uses lag_units_7d (D-7 value) on deterministic fixture
  5.  Seasonal naive falls back when lag_units_7d is null
  6.  Moving average uses rolling_units_mean_7d, not target_units_sold
  7.  Forecast rows are persisted to DB
  8.  Forecast rows include actual_units during backtest
  9.  absolute_error = |actual - forecast| per row
  10. squared_error = (actual - forecast)^2 per row
  11. WAPE is computed correctly
  12. SMAPE handles zero denominators safely (row contributes 0)
  13. Bias is computed correctly
  14. Model metrics are persisted to model_metrics table
  15. Metrics computed at "overall" level
  16. Metrics computed at "category" and "store" levels
  17. ForecastRun record status is "completed" after successful run
  18. Baseline forecast is clear-before-rewrite safe (idempotent re-runs)
  19. POST /api/forecasts/baseline/run works
  20. GET /api/forecasts/runs works
  21. GET /api/forecasts/latest works
  22. GET /api/forecasts/product/{product_id} works
  23. GET /api/model-metrics works
  24. /api/data-health includes real forecast counts after baseline run
  25. No stockout/reorder/ML fields in forecast or metric schema
  26. Existing Sprint 0–3 tests still pass (integrity guard)
"""

import math
import pytest
from datetime import date, timedelta, datetime
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.main import app
from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
from app.services.ingestion_service import IngestionService
from app.services.aggregation_service import AggregationService
from app.services.feature_service import FeatureService
from app.services.forecasting_service import ForecastingService, VALID_MODEL_TYPES
from app.db.models import (
    FeatureMatrix, FeatureRun, ForecastRun, Forecast, ModelMetric,
)

client = TestClient(app)

# Small but sufficient: 91 days gives 35 days warmup + 56-day test window
FORECAST_CONFIG = MockConfig(
    seed=42,
    product_count=4,
    store_count=2,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 3, 31),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_db(override_db):
    yield


@pytest.fixture
def full_pipeline_db(in_memory_db):
    """Seed → ingest → aggregate → features. Return (db, feature_result)."""
    connector = MockCommerceConnector(FORECAST_CONFIG)
    IngestionService(connector, in_memory_db).run(
        FORECAST_CONFIG.start_date, FORECAST_CONFIG.end_date
    )
    AggregationService(in_memory_db).run_full_aggregation(
        FORECAST_CONFIG.start_date, FORECAST_CONFIG.end_date
    )
    feat_result = FeatureService(in_memory_db).build_feature_matrix()
    return in_memory_db, feat_result


@pytest.fixture
def forecast_db(full_pipeline_db):
    """Full pipeline + seasonal_naive forecast. Return (db, forecast_result)."""
    db, _ = full_pipeline_db
    svc = ForecastingService(db)
    result = svc.run_baseline_forecast(
        model_type="seasonal_naive",
        horizon_days=28,
        backtest_days=28,   # small window so tests are fast
    )
    return db, result


def _seed_minimal_feature_matrix(db, rows: list[dict]) -> None:
    """Insert pre-built FeatureMatrix rows for deterministic math tests."""
    now = datetime.utcnow()
    for r in rows:
        r.setdefault("created_at", now)
        r.setdefault("feature_run_id", "fr-test")
        r.setdefault("category", "Tops")
        r.setdefault("store_channel", "retail")
        r.setdefault("rolling_units_std_7d", 0.0)
        r.setdefault("rolling_units_std_28d", 0.0)
    db.bulk_insert_mappings(FeatureMatrix, rows)
    db.flush()


# ---------------------------------------------------------------------------
# 1–3. Service can run each baseline model type
# ---------------------------------------------------------------------------

def test_seasonal_naive_baseline_runs(full_pipeline_db):
    db, _ = full_pipeline_db
    result = ForecastingService(db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=14
    )
    assert result["status"] == "completed"
    assert result["rows_created"] > 0
    assert "metrics" in result
    assert "overall" in result["metrics"]


def test_moving_average_7d_baseline_runs(full_pipeline_db):
    db, _ = full_pipeline_db
    result = ForecastingService(db).run_baseline_forecast(
        model_type="moving_average_7d", backtest_days=14
    )
    assert result["status"] == "completed"
    assert result["rows_created"] > 0


def test_moving_average_28d_baseline_runs(full_pipeline_db):
    db, _ = full_pipeline_db
    result = ForecastingService(db).run_baseline_forecast(
        model_type="moving_average_28d", backtest_days=14
    )
    assert result["status"] == "completed"
    assert result["rows_created"] > 0


# ---------------------------------------------------------------------------
# 4. Seasonal naive uses lag_units_7d on deterministic fixture
# ---------------------------------------------------------------------------

def test_seasonal_naive_uses_lag_7d(in_memory_db):
    """Seasonal naive forecast for D must equal lag_units_7d (units sold D-7)."""
    # Two dates: D-7 (train) and D (test); last date in window = D
    d_minus_7 = date(2024, 2, 1)
    d = date(2024, 2, 8)   # D-7 = 2024-02-01 → lag_units_7d should be 5.0

    rows = [
        {
            "id": "fm-early",
            "date": d_minus_7,
            "product_id": "p1", "store_id": "s1",
            "target_units_sold": 5.0,
            "lag_units_7d": None,
            "rolling_units_mean_7d": 3.0,
            "rolling_units_mean_28d": 2.5,
        },
        {
            "id": "fm-test",
            "date": d,
            "product_id": "p1", "store_id": "s1",
            "target_units_sold": 7.0,    # actual
            "lag_units_7d": 5.0,         # forecast signal: units sold on D-7
            "rolling_units_mean_7d": 3.2,
            "rolling_units_mean_28d": 2.8,
        },
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    result = ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive",
        backtest_days=1,   # test window = last 1 day = D only
    )

    assert result["status"] == "completed"
    frow = (
        in_memory_db.query(Forecast)
        .filter(Forecast.product_id == "p1", Forecast.store_id == "s1")
        .first()
    )
    assert frow is not None
    assert abs(frow.p50_units - 5.0) < 1e-6, (
        f"Expected seasonal naive p50=5.0 (lag_units_7d), got {frow.p50_units}"
    )


# ---------------------------------------------------------------------------
# 5. Seasonal naive fallback when lag_units_7d is null
# ---------------------------------------------------------------------------

def test_seasonal_naive_fallback_to_rolling_mean(in_memory_db):
    """When lag_units_7d is null, fall back to rolling_units_mean_7d."""
    d = date(2024, 2, 8)
    rows = [
        {
            "id": "fm-fb",
            "date": d,
            "product_id": "p1", "store_id": "s1",
            "target_units_sold": 4.0,
            "lag_units_7d": None,          # no lag available
            "rolling_units_mean_7d": 2.5,  # fallback
            "rolling_units_mean_28d": 2.0,
        }
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=1
    )

    frow = in_memory_db.query(Forecast).filter(Forecast.product_id == "p1").first()
    assert frow is not None
    assert abs(frow.p50_units - 2.5) < 1e-6, (
        f"Expected fallback p50=2.5 (rolling_mean_7d), got {frow.p50_units}"
    )


# ---------------------------------------------------------------------------
# 6. Moving average uses rolling_units_mean, not current target
# ---------------------------------------------------------------------------

def test_moving_average_uses_rolling_mean_not_target(in_memory_db):
    """
    Moving average forecast must read rolling_units_mean_7d (which covers D-7..D-1),
    not target_units_sold (which is D). Confirms no leakage via the 'wrong' column.
    """
    d = date(2024, 2, 10)
    rows = [
        {
            "id": "fm-ma",
            "date": d,
            "product_id": "p1", "store_id": "s1",
            "target_units_sold": 99.0,       # should NOT be used as forecast
            "lag_units_7d": 6.0,
            "rolling_units_mean_7d": 3.3,    # this should be the forecast
            "rolling_units_mean_28d": 2.8,
        }
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="moving_average_7d", backtest_days=1
    )

    frow = in_memory_db.query(Forecast).filter(Forecast.product_id == "p1").first()
    assert frow is not None
    assert abs(frow.p50_units - 3.3) < 1e-6, (
        f"Expected p50=rolling_mean_7d=3.3, got {frow.p50_units}"
    )
    assert abs(frow.actual_units - 99.0) < 1e-6, "actual_units must be target_units_sold"


# ---------------------------------------------------------------------------
# 7–8. Forecast rows persisted with actual_units
# ---------------------------------------------------------------------------

def test_forecast_rows_persisted(forecast_db):
    db, result = forecast_db
    count = db.query(func.count(Forecast.id)).scalar() or 0
    assert count == result["rows_created"]
    assert count > 0


def test_forecast_rows_have_actual_units(forecast_db):
    db, _ = forecast_db
    row = db.query(Forecast).first()
    assert row is not None
    assert row.actual_units is not None, "actual_units must be populated in backtest mode"


# ---------------------------------------------------------------------------
# 9. absolute_error = |actual - forecast|
# ---------------------------------------------------------------------------

def test_absolute_error_correct(in_memory_db):
    d = date(2024, 2, 10)
    rows = [
        {
            "id": "fm-ae",
            "date": d,
            "product_id": "p1", "store_id": "s1",
            "target_units_sold": 10.0,
            "lag_units_7d": 6.0,           # forecast = 6.0
            "rolling_units_mean_7d": 5.0,
            "rolling_units_mean_28d": 4.0,
        }
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=1
    )

    frow = in_memory_db.query(Forecast).filter(Forecast.product_id == "p1").first()
    assert frow is not None
    expected_ae = abs(10.0 - 6.0)  # = 4.0
    assert abs(frow.absolute_error - expected_ae) < 1e-6


# ---------------------------------------------------------------------------
# 10. squared_error = (actual - forecast)^2
# ---------------------------------------------------------------------------

def test_squared_error_correct(in_memory_db):
    d = date(2024, 2, 10)
    rows = [
        {
            "id": "fm-se",
            "date": d,
            "product_id": "p1", "store_id": "s1",
            "target_units_sold": 10.0,
            "lag_units_7d": 6.0,           # forecast = 6.0
            "rolling_units_mean_7d": 5.0,
            "rolling_units_mean_28d": 4.0,
        }
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=1
    )

    frow = in_memory_db.query(Forecast).filter(Forecast.product_id == "p1").first()
    expected_se = (10.0 - 6.0) ** 2  # = 16.0
    assert abs(frow.squared_error - expected_se) < 1e-6


# ---------------------------------------------------------------------------
# 11. WAPE computed correctly
# ---------------------------------------------------------------------------

def test_wape_computed_correctly(in_memory_db):
    """WAPE = sum(|actual - forecast|) / sum(actual) for known values."""
    # Two rows: (actual=10, forecast=8) and (actual=6, forecast=5)
    # sum_abs_err = |10-8| + |6-5| = 2 + 1 = 3
    # sum_actual  = 10 + 6 = 16
    # WAPE = 3/16 = 0.1875

    d1 = date(2024, 2, 9)
    d2 = date(2024, 2, 10)
    rows = [
        {
            "id": "wape-1",
            "date": d1, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 10.0, "lag_units_7d": 8.0,
            "rolling_units_mean_7d": 7.0, "rolling_units_mean_28d": 6.0,
        },
        {
            "id": "wape-2",
            "date": d2, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 6.0, "lag_units_7d": 5.0,
            "rolling_units_mean_7d": 5.5, "rolling_units_mean_28d": 5.0,
        },
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    result = ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=2
    )

    assert result["status"] == "completed"
    overall = result["metrics"]["overall"]
    expected_wape = 3.0 / 16.0
    assert abs(overall["wape"] - expected_wape) < 1e-6, (
        f"Expected WAPE={expected_wape:.4f}, got {overall['wape']}"
    )


# ---------------------------------------------------------------------------
# 12. SMAPE handles zero denominators safely
# ---------------------------------------------------------------------------

def test_smape_zero_denominator_safe(in_memory_db):
    """When both actual=0 and forecast=0, row SMAPE contribution must be 0 (not NaN/inf)."""
    d1 = date(2024, 2, 9)
    d2 = date(2024, 2, 10)
    rows = [
        {
            "id": "smape-zero",
            "date": d1, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 0.0, "lag_units_7d": 0.0,   # zero/zero case
            "rolling_units_mean_7d": 0.0, "rolling_units_mean_28d": 0.0,
        },
        {
            "id": "smape-nonzero",
            "date": d2, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 4.0, "lag_units_7d": 2.0,
            "rolling_units_mean_7d": 2.5, "rolling_units_mean_28d": 2.0,
        },
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    result = ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=2
    )

    assert result["status"] == "completed"
    overall = result["metrics"]["overall"]
    # smape must be a finite number, not NaN or inf
    assert overall["smape"] is not None
    assert math.isfinite(overall["smape"])
    assert overall["smape"] >= 0.0

    # Zero-row forecast should have absolute_percentage_error = 0
    zero_row = (
        in_memory_db.query(Forecast)
        .filter(Forecast.forecast_date == d1)
        .first()
    )
    assert zero_row is not None
    assert zero_row.absolute_percentage_error == 0.0


# ---------------------------------------------------------------------------
# 13. Bias computed correctly
# ---------------------------------------------------------------------------

def test_bias_computed_correctly(in_memory_db):
    """Bias = (sum(forecast) - sum(actual)) / sum(actual)."""
    # actual=[10, 6], forecast=[8, 5]
    # sum_forecast = 13, sum_actual = 16
    # bias = (13 - 16) / 16 = -0.1875

    d1 = date(2024, 2, 9)
    d2 = date(2024, 2, 10)
    rows = [
        {
            "id": "bias-1",
            "date": d1, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 10.0, "lag_units_7d": 8.0,
            "rolling_units_mean_7d": 8.0, "rolling_units_mean_28d": 8.0,
        },
        {
            "id": "bias-2",
            "date": d2, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 6.0, "lag_units_7d": 5.0,
            "rolling_units_mean_7d": 5.0, "rolling_units_mean_28d": 5.0,
        },
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    result = ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=2
    )

    overall = result["metrics"]["overall"]
    expected_bias = (13.0 - 16.0) / 16.0   # = -0.1875
    assert abs(overall["bias"] - expected_bias) < 1e-6, (
        f"Expected bias={expected_bias:.4f}, got {overall['bias']}"
    )


# ---------------------------------------------------------------------------
# 14–16. Metrics persisted at all levels
# ---------------------------------------------------------------------------

def test_model_metrics_persisted(forecast_db):
    db, result = forecast_db
    run_id = result["run_id"]
    count = db.query(func.count(ModelMetric.id)).scalar() or 0
    assert count > 0, "model_metrics table must have rows after a forecast run"


def test_overall_metric_exists(forecast_db):
    db, result = forecast_db
    run_id = result["run_id"]
    overall = (
        db.query(ModelMetric)
        .filter(ModelMetric.run_id == run_id, ModelMetric.level == "overall")
        .first()
    )
    assert overall is not None
    assert overall.mae is not None
    assert overall.rmse is not None


def test_category_and_store_metrics_exist(forecast_db):
    db, result = forecast_db
    run_id = result["run_id"]
    category_count = (
        db.query(func.count(ModelMetric.id))
        .filter(ModelMetric.run_id == run_id, ModelMetric.level == "category")
        .scalar() or 0
    )
    store_count = (
        db.query(func.count(ModelMetric.id))
        .filter(ModelMetric.run_id == run_id, ModelMetric.level == "store")
        .scalar() or 0
    )
    assert category_count > 0, "Category-level metrics must be persisted"
    assert store_count > 0, "Store-level metrics must be persisted"


# ---------------------------------------------------------------------------
# 17. ForecastRun status is "completed"
# ---------------------------------------------------------------------------

def test_forecast_run_status_completed(forecast_db):
    db, result = forecast_db
    run_id = result["run_id"]
    run = db.query(ForecastRun).filter(ForecastRun.id == run_id).first()
    assert run is not None
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.rows_created == result["rows_created"]


# ---------------------------------------------------------------------------
# 18. Clear-before-rewrite: second run replaces the first
# ---------------------------------------------------------------------------

def test_baseline_forecast_is_idempotent(full_pipeline_db):
    db, _ = full_pipeline_db
    svc = ForecastingService(db)

    r1 = svc.run_baseline_forecast(model_type="seasonal_naive", backtest_days=14)
    assert r1["status"] == "completed"
    run1_id = r1["run_id"]

    r2 = svc.run_baseline_forecast(model_type="seasonal_naive", backtest_days=14)
    assert r2["status"] == "completed"
    run2_id = r2["run_id"]

    # After second run, only run2 should exist for seasonal_naive
    all_runs = (
        db.query(ForecastRun)
        .filter(ForecastRun.model_type == "seasonal_naive")
        .all()
    )
    assert len(all_runs) == 1
    assert all_runs[0].id == run2_id, "First run must be cleaned up by second run"

    # Forecast rows belong only to run2
    old_rows = (
        db.query(Forecast)
        .filter(Forecast.forecast_run_id == run1_id)
        .count()
    )
    assert old_rows == 0, "Forecasts from run1 must be deleted"


# ---------------------------------------------------------------------------
# 19. POST /api/forecasts/baseline/run
# ---------------------------------------------------------------------------

def test_post_baseline_run_api(override_db):
    client.post("/api/demo/reset", json={"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91})
    client.post("/api/aggregation/run")
    client.post("/api/features/build")

    response = client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "seasonal_naive", "horizon_days": 14, "backtest_days": 14},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["rows_created"] > 0
    assert "metrics" in data
    assert "overall" in data["metrics"]


def test_post_baseline_run_invalid_model_type(override_db):
    response = client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "lightgbm"},   # not valid in Sprint 4
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 20. GET /api/forecasts/runs
# ---------------------------------------------------------------------------

def test_get_forecast_runs_empty(override_db):
    response = client.get("/api/forecasts/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert data["total"] == 0


def test_get_forecast_runs_after_run(override_db):
    client.post("/api/demo/reset", json={"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91})
    client.post("/api/aggregation/run")
    client.post("/api/features/build")
    client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "seasonal_naive", "backtest_days": 14},
    )

    response = client.get("/api/forecasts/runs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    run = data["runs"][0]
    assert run["status"] == "completed"
    assert run["model_type"] == "seasonal_naive"


# ---------------------------------------------------------------------------
# 21. GET /api/forecasts/latest
# ---------------------------------------------------------------------------

def test_get_latest_forecast_no_data(override_db):
    response = client.get("/api/forecasts/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_forecast"


def test_get_latest_forecast_after_run(override_db):
    client.post("/api/demo/reset", json={"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91})
    client.post("/api/aggregation/run")
    client.post("/api/features/build")
    client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "seasonal_naive", "backtest_days": 14},
    )

    response = client.get("/api/forecasts/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["run"] is not None
    assert data["sample_size"] > 0
    assert len(data["sample"]) > 0

    # Validate sample row shape
    row = data["sample"][0]
    for field in ["forecast_date", "product_id", "store_id", "p50_units", "actual_units"]:
        assert field in row, f"Missing field '{field}' in sample row"


# ---------------------------------------------------------------------------
# 22. GET /api/forecasts/product/{product_id}
# ---------------------------------------------------------------------------

def test_get_product_forecast_no_data(override_db):
    response = client.get("/api/forecasts/product/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("no_forecast", "ok")


def test_get_product_forecast_after_run(override_db):
    client.post("/api/demo/reset", json={"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91})
    client.post("/api/aggregation/run")
    client.post("/api/features/build")
    client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "seasonal_naive", "backtest_days": 14},
    )

    # Get any product_id that exists
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        first_row = db.query(Forecast).first()
        assert first_row is not None, "No forecasts found after run"
        product_id = first_row.product_id
    finally:
        db.close()

    response = client.get(f"/api/forecasts/product/{product_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["product_id"] == product_id
    assert len(data["rows"]) > 0


# ---------------------------------------------------------------------------
# 23. GET /api/model-metrics
# ---------------------------------------------------------------------------

def test_get_model_metrics_no_data(override_db):
    response = client.get("/api/model-metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_metrics"


def test_get_model_metrics_after_run(override_db):
    client.post("/api/demo/reset", json={"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91})
    client.post("/api/aggregation/run")
    client.post("/api/features/build")
    client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "seasonal_naive", "backtest_days": 14},
    )

    response = client.get("/api/model-metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["total"] > 0
    metric = data["metrics"][0]
    for field in ["model_type", "level", "level_value", "mae", "rmse", "wape", "smape", "bias"]:
        assert field in metric, f"Missing metric field '{field}'"


# ---------------------------------------------------------------------------
# 24. /api/data-health includes real forecast counts
# ---------------------------------------------------------------------------

def test_data_health_includes_forecast_counts(override_db):
    client.post("/api/demo/reset", json={"seed": 42, "product_count": 4, "store_count": 2, "history_days": 91})
    client.post("/api/aggregation/run")
    client.post("/api/features/build")
    client.post(
        "/api/forecasts/baseline/run",
        json={"model_type": "seasonal_naive", "backtest_days": 14},
    )

    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert "forecast_counts" in data
    assert data["forecast_counts"]["forecast_runs"] >= 1
    assert data["forecast_counts"]["forecasts"] > 0
    assert data["forecast_counts"]["model_metrics"] > 0
    assert data["latest_forecast_run"] is not None
    assert data["latest_forecast_run"]["status"] == "completed"


# ---------------------------------------------------------------------------
# 25. No stockout/reorder/ML fields introduced prematurely
# ---------------------------------------------------------------------------

def test_no_stockout_risk_fields_in_forecast_schema():
    """Forecast and ModelMetric ORM models must not have stockout/reorder fields."""
    forbidden = {
        "stockout_probability", "days_until_stockout", "risk_tier",
        "recommended_qty", "reorder_point", "economic_order_qty",
        "ml_model_id", "lightgbm_version", "xgboost_version",
    }
    forecast_cols = {c.key for c in Forecast.__table__.columns}
    metric_cols = {c.key for c in ModelMetric.__table__.columns}

    for field in forbidden:
        assert field not in forecast_cols, f"Forbidden field '{field}' in Forecast table"
        assert field not in metric_cols, f"Forbidden field '{field}' in ModelMetric table"


def test_wape_is_none_when_all_actuals_zero(in_memory_db):
    """WAPE denominator safety: when sum(actual)=0, WAPE must be None."""
    d = date(2024, 2, 10)
    rows = [
        {
            "id": "wape-zero",
            "date": d, "product_id": "p1", "store_id": "s1",
            "target_units_sold": 0.0,    # zero actual
            "lag_units_7d": 1.0,         # non-zero forecast
            "rolling_units_mean_7d": 1.0,
            "rolling_units_mean_28d": 1.0,
        }
    ]
    _seed_minimal_feature_matrix(in_memory_db, rows)

    result = ForecastingService(in_memory_db).run_baseline_forecast(
        model_type="seasonal_naive", backtest_days=1
    )

    overall = result["metrics"]["overall"]
    assert overall["wape"] is None, "WAPE must be None when sum(actual)=0"
    assert overall["bias"] is None, "Bias must be None when sum(actual)=0"
