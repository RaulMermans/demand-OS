"""
TrainingService — global ML demand forecasting model.

Sprint 5: HistGradientBoostingRegressor trained across all (product, store) series.

Pipeline:
  feature_matrix (leakage-safe, from FeatureService)
    → TrainingService.train_ml_forecaster()
    → model_versions table (registry entry + artifact path)
    → forecast_runs table (audit record)
    → forecasts table (predicted p50 + heuristic bands + actuals + errors)
    → model_metrics table (MAE, RMSE, WAPE, SMAPE, Bias at overall/category/store)

Design
------
One global model is trained across all (product, store) combinations simultaneously.
This transfers learning from high-volume to low-volume SKUs (global ML approach,
inspired by Nixtla/mlforecast and M5-style retail forecasting practice).

Feature encoding
----------------
Numerical features: filled with 0 when null (lag/rolling nulls at series start).
Categorical features: OrdinalEncoder with sorted categories for determinism.
  Categories fitted on training rows; unseen test categories → -1 (unknown).
  Encoded columns replace the original strings in the design matrix.

Leakage safety
--------------
Only rows BEFORE the backtest window are used for training.
Test rows are those with date >= (max_date - backtest_days + 1).
The target (target_units_sold) is never used as an input feature.

Artifact storage
----------------
Saved to {artifact_dir}/{model_version_id}.joblib as a dict:
  {"model": fitted_regressor, "encoder": fitted_encoder,
   "numeric_columns": [...], "categorical_columns": [...],
   "feature_columns": [...], "trained_at": "ISO"}
artifact_dir defaults to "models/forecasting" (relative to cwd).
Generated artifacts are excluded from git via .gitignore.

Baseline comparison
-------------------
After training, the service queries completed baseline runs and reports
whether ML beats the best baseline by WAPE. ML is not forced to win.

Reference: Nixtla/mlforecast (global ML patterns), M5 competition (28-day horizon).
External model code is not copied from these references.
"""

import logging
import math
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import OrdinalEncoder
from sqlalchemy.orm import Session

from app.db.models import (
    FeatureMatrix,
    Forecast,
    ForecastRun,
    ModelMetric,
    ModelVersion,
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# Feature column definitions
# -------------------------------------------------------------------------

NUMERIC_FEATURES: list[str] = [
    "lag_units_1d",
    "lag_units_7d",
    "lag_units_14d",
    "lag_units_28d",
    "rolling_units_mean_7d",
    "rolling_units_mean_14d",
    "rolling_units_mean_28d",
    "rolling_units_std_7d",
    "rolling_units_std_28d",
    "rolling_revenue_mean_7d",
    "rolling_revenue_mean_28d",
    "day_of_week",
    "week_of_year",
    "month",
    "quarter",
    "is_weekend",
    "promo_active",
    "discount_pct",
    "retail_price",
    "unit_cost",
    "gross_margin_pct",
    "price_change_pct_7d",
    "price_change_pct_28d",
    "available_units",
    "stockout_flag",
    "days_of_supply",
    "days_since_launch",
]

CATEGORICAL_FEATURES: list[str] = [
    "category",
    "store_channel",
    "product_age_bucket",
]

ALL_FEATURE_COLUMNS: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

TARGET_COLUMN = "target_units_sold"

# Fields that must never appear as model inputs
FORBIDDEN_INPUT_FIELDS: set[str] = {
    "forecast",
    "forecast_7d",
    "forecast_28d",
    "forecast_90d",
    "actual_units",
    "absolute_error",
    "squared_error",
    "risk_score",
    "stockout_risk",
    "recommended_units",
    "reorder_quantity",
    "future_demand",
    "future_units_sold",
}

BASELINE_MODEL_TYPES = frozenset(
    {"seasonal_naive", "moving_average_7d", "moving_average_28d"}
)


def _safe_float(val: Any) -> float | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class TrainingService:
    def __init__(self, db: Session, artifact_dir: str | None = None):
        self.db = db
        self.artifact_dir = artifact_dir or "models/forecasting"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def train_ml_forecaster(
        self,
        algorithm: str = "hist_gradient_boosting",
        horizon_days: int = 28,
        backtest_days: int = 56,
        source_feature_run_id: str | None = None,
    ) -> dict:
        """
        Train an ML global forecaster from feature_matrix.

        Steps:
          1. Load feature_matrix rows
          2. Split train / test by date
          3. Encode categoricals (OrdinalEncoder, sorted for determinism)
          4. Fit HistGradientBoostingRegressor on train rows
          5. Predict test rows; clip predictions ≥ 0
          6. Persist forecast rows, metrics, model version, artifact
          7. Compare against best completed baseline
          8. Return summary dict

        algorithm must be "hist_gradient_boosting" (only supported value in Sprint 5).
        """
        if algorithm != "hist_gradient_boosting":
            raise ValueError(
                f"Unsupported algorithm '{algorithm}'. "
                "Only 'hist_gradient_boosting' is supported in Sprint 5."
            )

        # Guard: verify no forbidden fields bleed into feature list
        forbidden_overlap = FORBIDDEN_INPUT_FIELDS & set(ALL_FEATURE_COLUMNS)
        if forbidden_overlap:
            raise RuntimeError(
                f"Feature safety violation: {forbidden_overlap} in feature columns"
            )

        model_version_id = f"model-{uuid.uuid4()}"
        run_id = f"forecast-run-{uuid.uuid4()}"

        # Register model version as "running"
        mv = ModelVersion(
            id=model_version_id,
            model_name="HistGradientBoostingRegressor",
            algorithm=algorithm,
            model_type="ml_global_regressor",
            status="running",
            trained_at=datetime.utcnow(),
            feature_run_id=source_feature_run_id,
            feature_columns_json=ALL_FEATURE_COLUMNS,
            target_column=TARGET_COLUMN,
            config_json={
                "horizon_days": horizon_days,
                "backtest_days": backtest_days,
                "source_feature_run_id": source_feature_run_id,
            },
            created_at=datetime.utcnow(),
        )
        self.db.add(mv)
        self.db.flush()

        run = ForecastRun(
            id=run_id,
            model_name=algorithm,
            model_type=algorithm,
            horizon_days=horizon_days,
            backtest_mode=True,
            mode="backtest",
            status="running",
            started_at=datetime.utcnow(),
            model_version_id=model_version_id,
            config_json={
                "backtest_days": backtest_days,
                "algorithm": algorithm,
                "source_feature_run_id": source_feature_run_id,
            },
        )
        self.db.add(run)
        self.db.flush()

        try:
            df = self._load_feature_matrix(source_feature_run_id)
            if df.empty:
                return self._fail(mv, run, "feature_matrix is empty — run POST /api/features/build first")

            # Date split
            max_date = df["date_only"].max()
            min_date = df["date_only"].min()
            test_start = max_date - timedelta(days=backtest_days - 1)
            test_end = max_date
            train_end = test_start - timedelta(days=1)

            train_df = df[df["date_only"] < test_start].copy()
            test_df = df[df["date_only"] >= test_start].copy()

            if train_df.empty:
                return self._fail(mv, run, f"No training rows before {test_start}")
            if test_df.empty:
                return self._fail(mv, run, f"No test rows from {test_start} to {test_end}")

            # Feature engineering: encode categoricals
            encoder = self._fit_encoder(train_df)
            X_train, y_train = self._build_X_y(train_df, encoder)
            X_test, _ = self._build_X_y(test_df, encoder)

            # Train
            regressor = HistGradientBoostingRegressor(
                max_iter=200,
                max_depth=6,
                learning_rate=0.05,
                l2_regularization=0.1,
                random_state=42,
            )
            regressor.fit(X_train, y_train)

            # Predict and clip
            preds = regressor.predict(X_test)
            preds = np.clip(preds, 0.0, None)
            test_df = test_df.copy()
            test_df["p50_units"] = preds

            # Heuristic bands (±1σ of recent demand, same as Sprint 4 baselines)
            std = test_df["rolling_units_std_7d"].fillna(0.0)
            test_df["p10_units"] = (test_df["p50_units"] - std).clip(lower=0.0)
            test_df["p90_units"] = test_df["p50_units"] + std

            # Per-row error metrics
            act = test_df["actual_units"]
            fct = test_df["p50_units"]
            test_df["absolute_error"] = (act - fct).abs()
            test_df["squared_error"] = (act - fct) ** 2
            denom = act.abs() + fct.abs()
            test_df["absolute_percentage_error"] = (
                (2 * test_df["absolute_error"]) / denom
            ).where(denom > 0, other=0.0)

            # horizon_day ordinal
            base = pd.Timestamp(test_start)
            test_df["horizon_day"] = (test_df["date"] - base).dt.days + 1

            # Clear previous ML runs of same algorithm
            self._clear_previous_ml_runs(algorithm, run_id, model_version_id)

            # Persist forecast rows
            forecast_rows = self._build_forecast_rows(test_df, run_id, algorithm)
            self.db.bulk_insert_mappings(Forecast, forecast_rows)
            self.db.flush()

            # Metrics
            metrics_summary = self._compute_and_persist_metrics(
                test_df, run_id, algorithm, horizon_days
            )

            # Save artifact
            os.makedirs(self.artifact_dir, exist_ok=True)
            artifact_path = os.path.join(self.artifact_dir, f"{model_version_id}.joblib")
            joblib.dump(
                {
                    "model": regressor,
                    "encoder": encoder,
                    "numeric_columns": NUMERIC_FEATURES,
                    "categorical_columns": CATEGORICAL_FEATURES,
                    "feature_columns": ALL_FEATURE_COLUMNS,
                    "trained_at": datetime.utcnow().isoformat(),
                },
                artifact_path,
            )

            # Update model version
            mv.status = "completed"
            mv.artifact_path = artifact_path
            mv.training_start_date = min_date
            mv.training_end_date = train_end
            mv.test_start_date = test_start
            mv.test_end_date = test_end
            mv.training_cutoff_date = train_end
            mv.metrics_summary_json = metrics_summary
            mv.is_active = True

            # Update forecast run
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.rows_created = len(forecast_rows)
            run.train_start_date = min_date
            run.train_end_date = train_end
            run.test_start_date = test_start
            run.test_end_date = test_end

            self.db.commit()

            # Baseline comparison (after commit so baseline data is consistent)
            overall_wape = _safe_float(metrics_summary.get("overall", {}).get("wape"))
            comparison = self._compare_against_baselines(overall_wape)

            return {
                "status": "completed",
                "model_version_id": model_version_id,
                "algorithm": algorithm,
                "forecast_run_id": run_id,
                "rows_predicted": len(forecast_rows),
                "metrics": metrics_summary,
                "baseline_comparison": comparison,
                "artifact_path": artifact_path,
                "date_windows": {
                    "train_start": str(min_date),
                    "train_end": str(train_end),
                    "test_start": str(test_start),
                    "test_end": str(test_end),
                },
            }

        except Exception as exc:
            logger.exception("ML training run %s failed", model_version_id)
            self.db.rollback()
            mv.status = "failed"
            mv.error_message = str(exc)
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
            self.db.add(mv)
            self.db.add(run)
            self.db.commit()
            raise

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_feature_matrix(self, source_feature_run_id: str | None) -> pd.DataFrame:
        query = self.db.query(FeatureMatrix)
        if source_feature_run_id:
            query = query.filter(
                FeatureMatrix.feature_run_id == source_feature_run_id
            )
        rows = query.all()
        if not rows:
            return pd.DataFrame()

        records = []
        for r in rows:
            record: dict[str, Any] = {
                "date": r.date,
                "product_id": r.product_id,
                "store_id": r.store_id,
                "actual_units": r.target_units_sold if r.target_units_sold is not None else 0.0,
                # Numeric features
                "lag_units_1d": r.lag_units_1d,
                "lag_units_7d": r.lag_units_7d,
                "lag_units_14d": r.lag_units_14d,
                "lag_units_28d": r.lag_units_28d,
                "rolling_units_mean_7d": r.rolling_units_mean_7d,
                "rolling_units_mean_14d": r.rolling_units_mean_14d,
                "rolling_units_mean_28d": r.rolling_units_mean_28d,
                "rolling_units_std_7d": r.rolling_units_std_7d,
                "rolling_units_std_28d": r.rolling_units_std_28d,
                "rolling_revenue_mean_7d": r.rolling_revenue_mean_7d,
                "rolling_revenue_mean_28d": r.rolling_revenue_mean_28d,
                "day_of_week": r.day_of_week,
                "week_of_year": r.week_of_year,
                "month": r.month,
                "quarter": r.quarter,
                "is_weekend": int(r.is_weekend) if r.is_weekend is not None else 0,
                "promo_active": int(r.promo_active) if r.promo_active is not None else 0,
                "discount_pct": r.discount_pct,
                "retail_price": r.retail_price,
                "unit_cost": r.unit_cost,
                "gross_margin_pct": r.gross_margin_pct,
                "price_change_pct_7d": r.price_change_pct_7d,
                "price_change_pct_28d": r.price_change_pct_28d,
                "available_units": r.available_units,
                "stockout_flag": int(r.stockout_flag) if r.stockout_flag is not None else 0,
                "days_of_supply": r.days_of_supply,
                "days_since_launch": r.days_since_launch,
                # Categorical features
                "category": r.category or "unknown",
                "store_channel": r.store_channel or "unknown",
                "product_age_bucket": r.product_age_bucket or "unknown",
            }
            records.append(record)

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df["date_only"] = df["date"].dt.date
        return df

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def _fit_encoder(self, train_df: pd.DataFrame) -> OrdinalEncoder:
        """
        Fit OrdinalEncoder on training categorical columns.
        Categories are sorted alphabetically for determinism.
        Unseen values in inference → encoded as -1.
        """
        cats = []
        for col in CATEGORICAL_FEATURES:
            unique_vals = sorted(train_df[col].fillna("unknown").unique().tolist())
            cats.append(unique_vals)

        encoder = OrdinalEncoder(
            categories=cats,
            handle_unknown="use_encoded_value",
            unknown_value=-1,
            dtype=float,
        )
        encoder.fit(train_df[CATEGORICAL_FEATURES].fillna("unknown"))
        return encoder

    def _build_X_y(
        self,
        df: pd.DataFrame,
        encoder: OrdinalEncoder,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build design matrix X and label vector y."""
        num = df[NUMERIC_FEATURES].fillna(0.0).values.astype(float)
        cat = encoder.transform(df[CATEGORICAL_FEATURES].fillna("unknown"))
        X = np.hstack([num, cat])
        y = df["actual_units"].fillna(0.0).values.astype(float)
        return X, y

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def _clear_previous_ml_runs(
        self,
        algorithm: str,
        current_run_id: str,
        current_mv_id: str,
    ) -> None:
        prev_runs = (
            self.db.query(ForecastRun)
            .filter(
                ForecastRun.model_type == algorithm,
                ForecastRun.id != current_run_id,
            )
            .all()
        )
        for prev in prev_runs:
            self.db.query(Forecast).filter(
                Forecast.forecast_run_id == prev.id
            ).delete(synchronize_session=False)
            self.db.query(ModelMetric).filter(
                ModelMetric.run_id == prev.id
            ).delete(synchronize_session=False)
            if prev.model_version_id and prev.model_version_id != current_mv_id:
                old_mv = self.db.get(ModelVersion, prev.model_version_id)
                if old_mv:
                    self.db.delete(old_mv)
            self.db.delete(prev)
        if prev_runs:
            self.db.flush()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _build_forecast_rows(
        self, test_df: pd.DataFrame, run_id: str, algorithm: str
    ) -> list[dict]:
        df = test_df.copy()
        df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
        df["forecast_run_id"] = run_id
        df["model_name"] = algorithm
        df["model_type"] = algorithm
        df["created_at"] = datetime.utcnow()
        df["forecast_date"] = df["date"].dt.date

        cols = [
            "id", "forecast_run_id", "forecast_date", "product_id", "store_id",
            "horizon_day", "model_name", "model_type",
            "p50_units", "p10_units", "p90_units", "actual_units",
            "absolute_error", "squared_error", "absolute_percentage_error",
            "created_at",
        ]
        records = df[cols].to_dict("records")

        # Sanitize NaN → None for SQLAlchemy
        return [
            {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
            for r in records
        ]

    def _compute_and_persist_metrics(
        self,
        test_df: pd.DataFrame,
        run_id: str,
        algorithm: str,
        horizon_days: int,
    ) -> dict:
        metric_rows = []
        summary: dict[str, Any] = {}

        # Overall
        overall = self._compute_metric_values(test_df)
        summary["overall"] = overall
        metric_rows.append(
            self._metric_row(run_id, algorithm, horizon_days, "overall", "all", overall)
        )

        # By category
        if "category" in test_df.columns:
            for cat, grp in test_df.groupby("category", dropna=False):
                if cat is not None and not (isinstance(cat, float) and math.isnan(cat)):
                    m = self._compute_metric_values(grp)
                    metric_rows.append(
                        self._metric_row(run_id, algorithm, horizon_days, "category", str(cat), m)
                    )

        # By store
        for store_id, grp in test_df.groupby("store_id"):
            m = self._compute_metric_values(grp)
            metric_rows.append(
                self._metric_row(run_id, algorithm, horizon_days, "store", str(store_id), m)
            )

        self.db.bulk_insert_mappings(ModelMetric, metric_rows)
        self.db.flush()
        return summary

    def _compute_metric_values(self, df: pd.DataFrame) -> dict:
        n = len(df)
        if n == 0:
            return {"mae": None, "rmse": None, "wape": None, "smape": None, "bias": None, "rows_evaluated": 0}

        mae = float(df["absolute_error"].mean())
        rmse = float(math.sqrt(df["squared_error"].mean()))

        sum_actual = float(df["actual_units"].sum())
        sum_abs_err = float(df["absolute_error"].sum())
        wape = (sum_abs_err / sum_actual) if sum_actual > 0 else None

        smape = float(df["absolute_percentage_error"].mean())

        sum_forecast = float(df["p50_units"].sum())
        bias = ((sum_forecast - sum_actual) / sum_actual) if sum_actual > 0 else None

        return {
            "mae": mae, "rmse": rmse, "wape": wape,
            "smape": smape, "bias": bias, "rows_evaluated": n,
        }

    def _metric_row(
        self,
        run_id: str,
        algorithm: str,
        horizon_days: int,
        level: str,
        level_value: str,
        metrics: dict,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "model_name": algorithm,
            "model_type": algorithm,
            "horizon_days": horizon_days,
            "level": level,
            "level_value": level_value,
            "mae": _safe_float(metrics.get("mae")),
            "rmse": _safe_float(metrics.get("rmse")),
            "wape": _safe_float(metrics.get("wape")),
            "smape": _safe_float(metrics.get("smape")),
            "bias": _safe_float(metrics.get("bias")),
            "rows_evaluated": metrics.get("rows_evaluated", 0),
            "created_at": datetime.utcnow(),
        }

    # ------------------------------------------------------------------
    # Baseline comparison
    # ------------------------------------------------------------------

    def _compare_against_baselines(self, ml_wape: float | None) -> dict:
        """
        Find the best completed baseline run by lowest WAPE.
        Reports honestly: ML is not forced to win.
        """
        best_run = None
        best_wape = None

        for mt in BASELINE_MODEL_TYPES:
            run = (
                self.db.query(ForecastRun)
                .filter(
                    ForecastRun.model_type == mt,
                    ForecastRun.status == "completed",
                )
                .order_by(ForecastRun.started_at.desc())
                .first()
            )
            if run is None:
                continue
            mm = (
                self.db.query(ModelMetric)
                .filter(
                    ModelMetric.run_id == run.id,
                    ModelMetric.level == "overall",
                )
                .first()
            )
            if mm and mm.wape is not None:
                if best_wape is None or mm.wape < best_wape:
                    best_wape = mm.wape
                    best_run = run

        if best_run is None:
            return {
                "available": False,
                "message": "No completed baseline runs to compare against. Run POST /api/forecasts/baseline/run first.",
            }

        wape_delta: float | None = None
        ml_won: bool | None = None
        if ml_wape is not None and best_wape is not None:
            wape_delta = round(ml_wape - best_wape, 6)
            ml_won = ml_wape < best_wape

        return {
            "available": True,
            "best_baseline_model_type": best_run.model_type,
            "best_baseline_wape": best_wape,
            "ml_wape": ml_wape,
            "wape_delta": wape_delta,
            "ml_won_against_baseline": ml_won,
        }

    # ------------------------------------------------------------------
    # Error helper
    # ------------------------------------------------------------------

    def _fail(self, mv: ModelVersion, run: ForecastRun, message: str) -> dict:
        mv.status = "failed"
        mv.error_message = message
        run.status = "failed"
        run.error_message = message
        run.completed_at = datetime.utcnow()
        self.db.commit()
        return {"status": "failed", "error": message}
