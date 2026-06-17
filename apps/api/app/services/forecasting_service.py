"""
ForecastingService — baseline demand forecasting with backtesting.

Sprint 4: Seasonal naive and moving-average baseline models.

Pipeline:
  feature_matrix (leakage-safe, from FeatureService)
    → ForecastingService.run_baseline_forecast()
    → forecasts table (p50 + heuristic p10/p90 bands + actuals + errors)
    → model_metrics table (MAE, RMSE, WAPE, SMAPE, Bias)
    → forecast_runs table (audit record)

Baseline models
---------------
seasonal_naive:
  forecast(D) = lag_units_7d(D)  [units sold on D-7]
  Fallback chain: lag_units_7d → rolling_units_mean_7d → rolling_units_mean_28d → 0.0
  Rationale: captures the weekly seasonality dominant in retail demand.

moving_average_7d:
  forecast(D) = rolling_units_mean_7d(D)  [mean over D-7..D-1]
  Fallback: 0.0

moving_average_28d:
  forecast(D) = rolling_units_mean_28d(D)  [mean over D-28..D-1]
  Fallback: 0.0

All forecast signals are read from the leakage-safe feature_matrix.
lag/rolling features in feature_matrix use shift(1), so they cover [D-W..D-1]
and never include the target date D — no leakage by construction.

P10/P90 uncertainty bands (heuristic, NOT probabilistic intervals)
------------------------------------------------------------------
seasonal_naive / moving_average_7d:
  std  = rolling_units_std_7d (0.0 when null)
  p10  = max(0, p50 - std)
  p90  = p50 + std
moving_average_28d:
  std  = rolling_units_std_28d (0.0 when null)
  p10  = max(0, p50 - std)
  p90  = p50 + std
Coverage guarantees are NOT provided for these heuristic bands.

Metrics
-------
MAE  = mean(|actual - forecast|)
RMSE = sqrt(mean((actual - forecast)²))
WAPE = sum(|actual - forecast|) / sum(actual)  — None when sum(actual)=0
SMAPE = mean(2·|forecast-actual| / (|actual|+|forecast|))  — row=0 when denominator=0
Bias = (sum(forecast) - sum(actual)) / sum(actual)  — None when sum(actual)=0

Metrics are persisted at levels: overall, category, store.

Backtesting window
------------------
test period  = last backtest_days of the feature_matrix date range
train period = everything before the test period (informational; baselines don't train)
Each test row is a 1-step-ahead prediction (horizon_day=1) using features as of D-1.

Idempotency
-----------
Before writing, all previous runs of the same model_type are deleted (clear-before-rewrite).
Running at most one completed run per model_type is guaranteed.

Reference: M5-style retail forecasting discipline and Nixtla/mlforecast feature patterns.
External ML library code is not copied here.
"""

import logging
import math
import uuid
from datetime import datetime, timedelta, date

import pandas as pd
import numpy as np

from sqlalchemy.orm import Session

from app.db.models import FeatureMatrix, ForecastRun, Forecast, ModelMetric

logger = logging.getLogger(__name__)

VALID_MODEL_TYPES = {"seasonal_naive", "moving_average_7d", "moving_average_28d"}


def _safe_float(val) -> float | None:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class ForecastingService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run_baseline_forecast(
        self,
        model_type: str,
        horizon_days: int = 28,
        backtest_days: int = 56,
        source_feature_run_id: str | None = None,
    ) -> dict:
        """
        Run a baseline forecast with historical backtesting.

        Reads feature_matrix, applies the chosen baseline, evaluates against
        actuals, persists forecast rows and metrics, returns a summary dict.
        """
        if model_type not in VALID_MODEL_TYPES:
            raise ValueError(
                f"Unknown model_type '{model_type}'. "
                f"Must be one of {sorted(VALID_MODEL_TYPES)}"
            )

        run_id = f"forecast-run-{uuid.uuid4()}"
        run = ForecastRun(
            id=run_id,
            model_name=model_type,
            model_type=model_type,
            horizon_days=horizon_days,
            backtest_mode=True,
            status="running",
            started_at=datetime.utcnow(),
            config_json={
                "backtest_days": backtest_days,
                "source_feature_run_id": source_feature_run_id,
            },
        )
        self.db.add(run)
        self.db.flush()

        try:
            df = self._load_feature_matrix(source_feature_run_id)
            if df.empty:
                run.status = "failed"
                run.error_message = (
                    "feature_matrix is empty — run POST /api/features/build first"
                )
                run.completed_at = datetime.utcnow()
                self.db.commit()
                return {
                    "status": "failed",
                    "run_id": run_id,
                    "error": "feature_matrix is empty",
                }

            # Determine date windows
            max_date = df["date"].max().date() if hasattr(df["date"].max(), "date") else df["date"].max()
            min_date = df["date"].min().date() if hasattr(df["date"].min(), "date") else df["date"].min()
            test_start = max_date - timedelta(days=backtest_days - 1)
            test_end = max_date
            train_end = test_start - timedelta(days=1)

            run.train_start_date = min_date
            run.train_end_date = train_end if train_end >= min_date else None
            run.test_start_date = test_start
            run.test_end_date = test_end
            self.db.flush()

            # Isolate the test window
            test_df = df[df["date_only"] >= test_start].copy()
            if test_df.empty:
                run.status = "failed"
                run.error_message = (
                    f"No feature rows in test window [{test_start}..{test_end}]"
                )
                run.completed_at = datetime.utcnow()
                self.db.commit()
                return {"status": "failed", "run_id": run_id, "error": run.error_message}

            # Generate baseline forecasts
            test_df = self._apply_baseline(test_df, model_type)

            # horizon_day = ordinal position in test window (1-indexed)
            base = pd.Timestamp(test_start)
            test_df["horizon_day"] = (test_df["date"] - base).dt.days + 1

            # Per-row error metrics
            act = test_df["actual_units"]
            fct = test_df["p50_units"]
            test_df["absolute_error"] = (act - fct).abs()
            test_df["squared_error"] = (act - fct) ** 2
            denom = act.abs() + fct.abs()
            test_df["absolute_percentage_error"] = (
                (2 * test_df["absolute_error"]) / denom
            ).where(denom > 0, other=0.0)

            # Clear previous runs of same model_type (idempotency)
            self._clear_previous_runs(model_type, run_id)

            # Persist forecast rows
            rows = self._build_forecast_rows(test_df, run_id, model_type)
            self.db.bulk_insert_mappings(Forecast, rows)
            self.db.flush()

            # Compute and persist metrics
            metrics_summary = self._compute_and_persist_metrics(
                test_df, run_id, model_type, horizon_days
            )

            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.rows_created = len(rows)
            self.db.commit()

            return {
                "status": "completed",
                "run_id": run_id,
                "model_type": model_type,
                "horizon_days": horizon_days,
                "backtest_days": backtest_days,
                "rows_created": len(rows),
                "date_windows": {
                    "train_start": str(min_date),
                    "train_end": str(train_end),
                    "test_start": str(test_start),
                    "test_end": str(test_end),
                },
                "metrics": metrics_summary,
            }

        except Exception as exc:
            logger.exception("Baseline forecast run %s failed", run_id)
            self.db.rollback()
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.utcnow()
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

        records = [
            {
                "date": r.date,
                "product_id": r.product_id,
                "store_id": r.store_id,
                "actual_units": r.target_units_sold if r.target_units_sold is not None else 0.0,
                "lag_units_7d": r.lag_units_7d,
                "rolling_units_mean_7d": r.rolling_units_mean_7d,
                "rolling_units_mean_28d": r.rolling_units_mean_28d,
                "rolling_units_std_7d": r.rolling_units_std_7d,
                "rolling_units_std_28d": r.rolling_units_std_28d,
                "category": r.category,
                "store_channel": r.store_channel,
                "feature_run_id": r.feature_run_id,
            }
            for r in rows
        ]

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df["date_only"] = df["date"].dt.date
        return df

    # ------------------------------------------------------------------
    # Baseline models
    # ------------------------------------------------------------------

    def _apply_baseline(self, test_df: pd.DataFrame, model_type: str) -> pd.DataFrame:
        df = test_df.copy()

        if model_type == "seasonal_naive":
            # Fallback chain: lag_7d → rolling_mean_7d → rolling_mean_28d → 0
            df["p50_units"] = (
                df["lag_units_7d"]
                .fillna(df["rolling_units_mean_7d"])
                .fillna(df["rolling_units_mean_28d"])
                .fillna(0.0)
                .clip(lower=0.0)
            )
            std = df["rolling_units_std_7d"].fillna(0.0)

        elif model_type == "moving_average_7d":
            df["p50_units"] = (
                df["rolling_units_mean_7d"].fillna(0.0).clip(lower=0.0)
            )
            std = df["rolling_units_std_7d"].fillna(0.0)

        elif model_type == "moving_average_28d":
            df["p50_units"] = (
                df["rolling_units_mean_28d"].fillna(0.0).clip(lower=0.0)
            )
            std = df["rolling_units_std_28d"].fillna(0.0)

        else:
            raise ValueError(f"Unsupported model_type: {model_type}")

        # Simple ±1σ heuristic bands (not probabilistic)
        df["p10_units"] = (df["p50_units"] - std).clip(lower=0.0)
        df["p90_units"] = df["p50_units"] + std

        return df

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _clear_previous_runs(self, model_type: str, current_run_id: str) -> None:
        prev_runs = (
            self.db.query(ForecastRun)
            .filter(
                ForecastRun.model_type == model_type,
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
            self.db.delete(prev)
        if prev_runs:
            self.db.flush()

    def _build_forecast_rows(
        self, test_df: pd.DataFrame, run_id: str, model_type: str
    ) -> list[dict]:
        df = test_df.copy()
        df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
        df["forecast_run_id"] = run_id
        df["model_name"] = model_type
        df["model_type"] = model_type
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
        clean = []
        for r in records:
            clean.append({
                k: (None if isinstance(v, float) and math.isnan(v) else v)
                for k, v in r.items()
            })
        return clean

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _compute_and_persist_metrics(
        self,
        test_df: pd.DataFrame,
        run_id: str,
        model_type: str,
        horizon_days: int,
    ) -> dict:
        metric_rows = []
        summary = {}

        # Overall
        overall = self._compute_metric_values(test_df)
        summary["overall"] = overall
        metric_rows.append(
            self._metric_row(run_id, model_type, horizon_days, "overall", "all", overall)
        )

        # By category
        if "category" in test_df.columns:
            for cat, grp in test_df.groupby("category", dropna=False):
                if cat is not None and not (isinstance(cat, float) and math.isnan(cat)):
                    m = self._compute_metric_values(grp)
                    metric_rows.append(
                        self._metric_row(
                            run_id, model_type, horizon_days, "category", str(cat), m
                        )
                    )

        # By store
        for store_id, grp in test_df.groupby("store_id"):
            m = self._compute_metric_values(grp)
            metric_rows.append(
                self._metric_row(
                    run_id, model_type, horizon_days, "store", str(store_id), m
                )
            )

        self.db.bulk_insert_mappings(ModelMetric, metric_rows)
        self.db.flush()
        return summary

    def _compute_metric_values(self, df: pd.DataFrame) -> dict:
        n = len(df)
        if n == 0:
            return {
                "mae": None, "rmse": None, "wape": None,
                "smape": None, "bias": None, "rows_evaluated": 0,
            }

        mae = float(df["absolute_error"].mean())
        rmse = float(math.sqrt(df["squared_error"].mean()))

        sum_actual = float(df["actual_units"].sum())
        sum_abs_err = float(df["absolute_error"].sum())
        wape = (sum_abs_err / sum_actual) if sum_actual > 0 else None

        smape = float(df["absolute_percentage_error"].mean())

        sum_forecast = float(df["p50_units"].sum())
        bias = ((sum_forecast - sum_actual) / sum_actual) if sum_actual > 0 else None

        return {
            "mae": mae,
            "rmse": rmse,
            "wape": wape,
            "smape": smape,
            "bias": bias,
            "rows_evaluated": n,
        }

    def _metric_row(
        self,
        run_id: str,
        model_type: str,
        horizon_days: int,
        level: str,
        level_value: str,
        metrics: dict,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "model_name": model_type,
            "model_type": model_type,
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
