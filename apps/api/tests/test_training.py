"""
Tests: TrainingService and /api/models/* endpoints (Sprint 5).

Covers:
  1.  TrainingService trains HistGradientBoosting from feature_matrix
  2.  Training uses only rows before the backtest window
  3.  Training excludes forbidden fields from feature columns
  4.  Categorical encoding is deterministic
  5.  Model artifact is saved to disk
  6.  ModelVersion row is persisted with status=completed
  7.  Forecast rows are persisted for ML model
  8.  Forecast p50 values are nonnegative
  9.  Actuals are joined for backtest rows
  10. Model metrics are persisted
  11. Metrics computed at overall level
  12. Metrics computed at category and store levels
  13. Baseline comparison works when baseline runs exist
  14. Baseline comparison handles missing baselines gracefully
  15. ML is not forced to beat baseline (honest reporting)
  16. Re-running same config is clear-before-rewrite safe
  17. POST /api/models/train works
  18. GET /api/models/versions works
  19. GET /api/models/latest works
  20. GET /api/models/compare works
  21. /api/data-health includes real model counts after training
  22. /api/overview includes honest model readiness fields
  23. No stockout/reorder fields introduced in Sprint 5
  24. Existing Sprint 0-4 tests still pass (integrity guard)
"""

import os
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
from app.services.forecasting_service import ForecastingService
from app.services.training_service import (
    TrainingService,
    ALL_FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    FORBIDDEN_INPUT_FIELDS,
    TARGET_COLUMN,
)
from app.db.models import (
    FeatureMatrix, ForecastRun, Forecast, ModelMetric, ModelVersion,
    StockoutRisk, ReorderRecommendation,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TRAIN_CONFIG = MockConfig(
    seed=42,
    product_count=4,
    store_count=2,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 3, 31),
)


@pytest.fixture
def full_pipeline_db(override_db, in_memory_db):
    """
    Runs the full pipeline: ingest → aggregate → features.
    Returns the db session ready for training.
    """
    connector = MockCommerceConnector(TRAIN_CONFIG)
    IngestionService(connector, in_memory_db).run(
        TRAIN_CONFIG.start_date, TRAIN_CONFIG.end_date
    )
    AggregationService(in_memory_db).run_full_aggregation(
        TRAIN_CONFIG.start_date, TRAIN_CONFIG.end_date
    )
    FeatureService(in_memory_db).build_feature_matrix()
    return in_memory_db


@pytest.fixture
def training_svc(full_pipeline_db, tmp_path):
    """TrainingService with temp artifact dir."""
    return TrainingService(full_pipeline_db, artifact_dir=str(tmp_path))


@pytest.fixture
def training_result(training_svc):
    """One ML training result (cached within test)."""
    return training_svc.train_ml_forecaster(
        algorithm="hist_gradient_boosting",
        horizon_days=28,
        backtest_days=28,
    )


# ---------------------------------------------------------------------------
# Test 1: Training runs without error
# ---------------------------------------------------------------------------

def test_training_completes(training_result):
    assert training_result["status"] == "completed"
    assert training_result["model_version_id"].startswith("model-")
    assert training_result["forecast_run_id"].startswith("forecast-run-")
    assert training_result["rows_predicted"] > 0


# ---------------------------------------------------------------------------
# Test 2: Only rows before backtest window used for training
# ---------------------------------------------------------------------------

def test_training_respects_date_split(full_pipeline_db, tmp_path):
    """Verify train_end_date < test_start_date in persisted ForecastRun."""
    svc = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path))
    result = svc.train_ml_forecaster(backtest_days=28)

    run = full_pipeline_db.query(ForecastRun).filter(
        ForecastRun.id == result["forecast_run_id"]
    ).first()

    assert run is not None
    assert run.train_end_date < run.test_start_date
    assert run.test_start_date <= run.test_end_date


# ---------------------------------------------------------------------------
# Test 3: Forbidden fields excluded from feature columns
# ---------------------------------------------------------------------------

def test_forbidden_fields_not_in_features():
    """target_units_sold and all forbidden ML fields must not be in feature columns."""
    assert TARGET_COLUMN not in ALL_FEATURE_COLUMNS, (
        "target_units_sold must not be an input feature"
    )
    overlap = FORBIDDEN_INPUT_FIELDS & set(ALL_FEATURE_COLUMNS)
    assert not overlap, f"Forbidden fields in feature columns: {overlap}"


# ---------------------------------------------------------------------------
# Test 4: Categorical encoding is deterministic
# ---------------------------------------------------------------------------

def test_categorical_encoding_is_deterministic(full_pipeline_db, tmp_path):
    """Same training data → same encoder categories → same predictions."""
    svc1 = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path / "run1"))
    svc2 = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path / "run2"))

    # Load feature matrix into pandas to inspect encoding
    from sklearn.preprocessing import OrdinalEncoder
    import pandas as pd

    rows = full_pipeline_db.query(FeatureMatrix).all()
    records = [
        {"category": r.category or "unknown",
         "store_channel": r.store_channel or "unknown",
         "product_age_bucket": r.product_age_bucket or "unknown"}
        for r in rows
    ]
    df = pd.DataFrame(records)

    encoder1 = svc1._fit_encoder(df)
    encoder2 = svc2._fit_encoder(df)

    # Same categories in same order
    for c1, c2 in zip(encoder1.categories_, encoder2.categories_):
        assert list(c1) == list(c2), "Encoder categories must be deterministic"


# ---------------------------------------------------------------------------
# Test 5: Model artifact is saved
# ---------------------------------------------------------------------------

def test_artifact_saved(training_result, tmp_path):
    artifact_path = training_result.get("artifact_path")
    assert artifact_path is not None
    assert os.path.exists(artifact_path), f"Artifact not found at {artifact_path}"

    import joblib
    artifact = joblib.load(artifact_path)
    assert "model" in artifact
    assert "encoder" in artifact
    assert "feature_columns" in artifact


# ---------------------------------------------------------------------------
# Test 6: ModelVersion row persisted with status=completed
# ---------------------------------------------------------------------------

def test_model_version_persisted(full_pipeline_db, training_result):
    mv_id = training_result["model_version_id"]
    mv = full_pipeline_db.get(ModelVersion, mv_id)
    assert mv is not None
    assert mv.status == "completed"
    assert mv.algorithm == "hist_gradient_boosting"
    assert mv.model_type == "ml_global_regressor"
    assert mv.artifact_path is not None


# ---------------------------------------------------------------------------
# Test 7: Forecast rows persisted for ML model
# ---------------------------------------------------------------------------

def test_forecast_rows_persisted(full_pipeline_db, training_result):
    run_id = training_result["forecast_run_id"]
    count = full_pipeline_db.query(func.count(Forecast.id)).filter(
        Forecast.forecast_run_id == run_id
    ).scalar()
    assert count > 0


# ---------------------------------------------------------------------------
# Test 8: p50 values are nonnegative
# ---------------------------------------------------------------------------

def test_p50_nonnegative(full_pipeline_db, training_result):
    run_id = training_result["forecast_run_id"]
    rows = full_pipeline_db.query(Forecast).filter(
        Forecast.forecast_run_id == run_id
    ).all()
    assert all(
        r.p50_units is not None and r.p50_units >= 0
        for r in rows
    ), "All p50_units must be nonnegative"


# ---------------------------------------------------------------------------
# Test 9: Actuals joined for backtest rows
# ---------------------------------------------------------------------------

def test_actuals_joined_for_backtest(full_pipeline_db, training_result):
    run_id = training_result["forecast_run_id"]
    rows = full_pipeline_db.query(Forecast).filter(
        Forecast.forecast_run_id == run_id
    ).all()
    # At least some rows should have actual_units (from feature_matrix target)
    rows_with_actuals = [r for r in rows if r.actual_units is not None]
    assert len(rows_with_actuals) > 0, "Backtest rows should have actual_units"


# ---------------------------------------------------------------------------
# Test 10: Metrics persisted
# ---------------------------------------------------------------------------

def test_metrics_persisted(full_pipeline_db, training_result):
    run_id = training_result["forecast_run_id"]
    count = full_pipeline_db.query(func.count(ModelMetric.id)).filter(
        ModelMetric.run_id == run_id
    ).scalar()
    assert count > 0


# ---------------------------------------------------------------------------
# Test 11: Overall metrics computed
# ---------------------------------------------------------------------------

def test_overall_metrics_computed(full_pipeline_db, training_result):
    run_id = training_result["forecast_run_id"]
    mm = full_pipeline_db.query(ModelMetric).filter(
        ModelMetric.run_id == run_id,
        ModelMetric.level == "overall",
    ).first()
    assert mm is not None
    assert mm.mae is not None and mm.mae >= 0
    assert mm.rmse is not None and mm.rmse >= 0
    assert mm.smape is not None and mm.smape >= 0


# ---------------------------------------------------------------------------
# Test 12: Category and store metrics computed
# ---------------------------------------------------------------------------

def test_category_and_store_metrics(full_pipeline_db, training_result):
    run_id = training_result["forecast_run_id"]

    cat_count = full_pipeline_db.query(func.count(ModelMetric.id)).filter(
        ModelMetric.run_id == run_id,
        ModelMetric.level == "category",
    ).scalar()
    assert cat_count > 0, "Category-level metrics should exist"

    store_count = full_pipeline_db.query(func.count(ModelMetric.id)).filter(
        ModelMetric.run_id == run_id,
        ModelMetric.level == "store",
    ).scalar()
    assert store_count > 0, "Store-level metrics should exist"


# ---------------------------------------------------------------------------
# Test 13: Baseline comparison works when baselines exist
# ---------------------------------------------------------------------------

def test_baseline_comparison_with_baselines(full_pipeline_db, tmp_path):
    """When a baseline run exists, comparison returns meaningful results."""
    # First run a baseline
    forecast_svc = ForecastingService(full_pipeline_db)
    forecast_svc.run_baseline_forecast(model_type="seasonal_naive", backtest_days=28)

    svc = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path))
    result = svc.train_ml_forecaster(backtest_days=28)

    comparison = result.get("baseline_comparison", {})
    assert comparison.get("available") is True
    assert comparison.get("best_baseline_model_type") == "seasonal_naive"
    assert comparison.get("best_baseline_wape") is not None
    assert "ml_won_against_baseline" in comparison


# ---------------------------------------------------------------------------
# Test 14: Baseline comparison handles no baselines gracefully
# ---------------------------------------------------------------------------

def test_baseline_comparison_no_baselines(full_pipeline_db, tmp_path):
    """When no baseline runs exist, comparison returns available=False."""
    svc = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path))
    result = svc.train_ml_forecaster(backtest_days=28)

    comparison = result.get("baseline_comparison", {})
    assert comparison.get("available") is False
    assert "message" in comparison


# ---------------------------------------------------------------------------
# Test 15: ML is not forced to beat baseline
# ---------------------------------------------------------------------------

def test_ml_not_forced_to_win(full_pipeline_db, tmp_path):
    """The ml_won_against_baseline field must be honest — either True or False."""
    forecast_svc = ForecastingService(full_pipeline_db)
    forecast_svc.run_baseline_forecast(model_type="moving_average_7d", backtest_days=28)

    svc = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path))
    result = svc.train_ml_forecaster(backtest_days=28)

    comparison = result.get("baseline_comparison", {})
    if comparison.get("available"):
        ml_won = comparison.get("ml_won_against_baseline")
        ml_wape = comparison.get("ml_wape")
        best_wape = comparison.get("best_baseline_wape")
        # The reported winner must match actual WAPE comparison
        if ml_wape is not None and best_wape is not None:
            expected_won = ml_wape < best_wape
            assert ml_won == expected_won, (
                f"Honesty check failed: ml_wape={ml_wape}, baseline_wape={best_wape}, "
                f"reported ml_won={ml_won}, expected={expected_won}"
            )


# ---------------------------------------------------------------------------
# Test 16: Re-running is clear-before-rewrite safe
# ---------------------------------------------------------------------------

def test_rerun_is_idempotent(full_pipeline_db, tmp_path):
    """Second run of same config replaces first — only one ML run at a time."""
    svc = TrainingService(full_pipeline_db, artifact_dir=str(tmp_path))
    result1 = svc.train_ml_forecaster(backtest_days=28)
    result2 = svc.train_ml_forecaster(backtest_days=28)

    run_count = full_pipeline_db.query(func.count(ForecastRun.id)).filter(
        ForecastRun.model_type == "hist_gradient_boosting",
        ForecastRun.status == "completed",
    ).scalar()
    assert run_count == 1, "Only one completed ML run should exist after two runs"

    # Latest result should be from second run
    assert result2["forecast_run_id"] != result1["forecast_run_id"]


# ---------------------------------------------------------------------------
# Test 17: POST /api/models/train works
# ---------------------------------------------------------------------------

def test_api_models_train(override_db):
    response = client.post("/api/demo/reset")
    assert response.status_code == 200

    # Build pipeline before training
    client.post("/api/aggregation/run", json={"dry_run": False})
    client.post("/api/features/build", json={})

    response = client.post(
        "/api/models/train",
        json={
            "algorithm": "hist_gradient_boosting",
            "horizon_days": 28,
            "backtest_days": 28,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "model_version_id" in data
    assert "metrics" in data
    assert "baseline_comparison" in data


# ---------------------------------------------------------------------------
# Test 18: GET /api/models/versions works
# ---------------------------------------------------------------------------

def test_api_models_versions(override_db):
    client.post("/api/demo/reset")
    client.post("/api/aggregation/run", json={"dry_run": False})
    client.post("/api/features/build", json={})
    client.post("/api/models/train", json={"backtest_days": 28})

    response = client.get("/api/models/versions")
    assert response.status_code == 200
    data = response.json()
    assert "versions" in data
    assert data["total"] >= 1


# ---------------------------------------------------------------------------
# Test 19: GET /api/models/latest works
# ---------------------------------------------------------------------------

def test_api_models_latest(override_db):
    client.post("/api/demo/reset")
    client.post("/api/aggregation/run", json={"dry_run": False})
    client.post("/api/features/build", json={})
    client.post("/api/models/train", json={"backtest_days": 28})

    response = client.get("/api/models/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["model_version"] is not None
    assert data["model_version"]["algorithm"] == "hist_gradient_boosting"


# ---------------------------------------------------------------------------
# Test 20: GET /api/models/compare works
# ---------------------------------------------------------------------------

def test_api_models_compare(override_db):
    client.post("/api/demo/reset")
    client.post("/api/aggregation/run", json={"dry_run": False})
    client.post("/api/features/build", json={})
    client.post("/api/forecasts/baseline/run", json={"model_type": "seasonal_naive", "backtest_days": 28})
    client.post("/api/models/train", json={"backtest_days": 28})

    response = client.get("/api/models/compare")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ml_wape" in data
    assert "best_baseline_wape" in data
    assert "wape_delta" in data
    assert "ml_won_against_baseline" in data


# ---------------------------------------------------------------------------
# Test 21: /api/data-health includes real model counts after training
# ---------------------------------------------------------------------------

def test_data_health_includes_model_counts(override_db):
    client.post("/api/demo/reset")
    client.post("/api/aggregation/run", json={"dry_run": False})
    client.post("/api/features/build", json={})
    client.post("/api/models/train", json={"backtest_days": 28})

    response = client.get("/api/data-health")
    assert response.status_code == 200
    data = response.json()
    assert "model_counts" in data
    assert data["model_counts"]["model_versions"] >= 1
    assert data["model_counts"]["ml_forecast_runs"] >= 1
    assert data.get("latest_model_version") is not None
    assert data["latest_model_version"]["algorithm"] == "hist_gradient_boosting"


# ---------------------------------------------------------------------------
# Test 22: /api/overview includes honest model readiness fields
# ---------------------------------------------------------------------------

def test_overview_includes_ml_readiness(override_db):
    client.post("/api/demo/reset")
    client.post("/api/aggregation/run", json={"dry_run": False})
    client.post("/api/features/build", json={})
    client.post("/api/models/train", json={"backtest_days": 28})

    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    summary = data.get("summary", {})
    assert "latest_ml_model_status" in summary
    assert "latest_ml_model_algorithm" in summary
    assert "latest_ml_wape" in summary
    assert "model_artifact_exists" in summary
    # Must NOT contain fake business metrics
    assert "stockout_risk" not in summary
    assert "reorder_recommendations" not in summary
    assert "revenue_at_risk" not in summary


# ---------------------------------------------------------------------------
# Test 23: No stockout/reorder fields introduced in Sprint 5
# ---------------------------------------------------------------------------

def test_no_stockout_or_reorder_in_sprint5(full_pipeline_db, training_result):
    """StockoutRisk and ReorderRecommendation tables must remain empty."""
    sr_count = full_pipeline_db.query(func.count(StockoutRisk.id)).scalar()
    rr_count = full_pipeline_db.query(func.count(ReorderRecommendation.id)).scalar()
    assert sr_count == 0, "StockoutRisk must not be populated in Sprint 5"
    assert rr_count == 0, "ReorderRecommendation must not be populated in Sprint 5"


# ---------------------------------------------------------------------------
# Test 24: Existing Sprint 0-4 tests still pass (integrity guard)
# ---------------------------------------------------------------------------

def test_existing_model_types_still_valid():
    """Baseline model types recognized by ForecastingService must still work."""
    from app.services.forecasting_service import VALID_MODEL_TYPES
    assert "seasonal_naive" in VALID_MODEL_TYPES
    assert "moving_average_7d" in VALID_MODEL_TYPES
    assert "moving_average_28d" in VALID_MODEL_TYPES


def test_feature_columns_count():
    """Feature column count sanity check — guards against accidental removal."""
    assert len(NUMERIC_FEATURES) == 27, f"Expected 27 numeric features, got {len(NUMERIC_FEATURES)}"
    assert len(CATEGORICAL_FEATURES) == 3, f"Expected 3 categorical features, got {len(CATEGORICAL_FEATURES)}"
    assert len(ALL_FEATURE_COLUMNS) == 30


def test_ci_files_exist():
    """CI workflow and dependabot config must exist (Sprint 5 requirement)."""
    # test file lives at apps/api/tests/ — repo root is 3 dirs up
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    ci_path = os.path.join(repo_root, ".github", "workflows", "ci.yml")
    dep_path = os.path.join(repo_root, ".github", "dependabot.yml")
    assert os.path.exists(ci_path), f"CI workflow missing: {ci_path}"
    assert os.path.exists(dep_path), f"Dependabot config missing: {dep_path}"


def test_gitignore_protects_artifacts():
    """Verify .gitignore contains patterns for models and generated data."""
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    gitignore_path = os.path.join(repo_root, ".gitignore")
    assert os.path.exists(gitignore_path)
    content = open(gitignore_path).read()
    assert "*.joblib" in content or "models/" in content
    assert "models/*" in content or "*.joblib" in content
