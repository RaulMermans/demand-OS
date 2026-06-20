"""
DemoPipelineService — orchestrates the full DemandOS demo pipeline.

Runs all 8 stages in sequence:
  1. reset_demo      — clear and re-seed raw data via IngestionService
  2. aggregation     — build canonical daily tables via AggregationService
  3. features        — build feature matrix via FeatureService
  4. baseline_forecast — run seasonal-naive baseline via ForecastingService
  5. train_ml        — train ML forecaster via TrainingService
  6. planning_forecast — generate forward-looking forecasts via ForecastingService
  7. stockout_risk   — score stockout risk via StockoutService
  8. recommendations — generate reorder recommendations via RecommendationService

Rules:
- Stops on the first failed step; subsequent steps are not attempted.
- All steps delegate to existing services — no duplicate business logic.
- A DemoPipelineRun record is created and updated throughout.
- No external API calls, no purchase orders, no email/Slack.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import DemoPipelineRun, RawOrder
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

# Ordered step definitions — each step has a name, display label, and kwargs factory.
_STEP_NAMES = [
    "reset_demo",
    "aggregation",
    "features",
    "baseline_forecast",
    "train_ml",
    "planning_forecast",
    "stockout_risk",
    "recommendations",
]

_STEP_LABELS = {
    "reset_demo": "Reset Demo Data",
    "aggregation": "Aggregation",
    "features": "Feature Build",
    "baseline_forecast": "Baseline Forecast",
    "train_ml": "ML Model Training",
    "planning_forecast": "Planning Forecast",
    "stockout_risk": "Stockout Risk",
    "recommendations": "Recommendations",
}


def _step_record(name: str) -> dict:
    return {
        "step_name": name,
        "step_label": _STEP_LABELS[name],
        "status": "pending",
        "started_at": None,
        "completed_at": None,
        "result_summary": None,
        "error_message": None,
    }


class DemoPipelineService:
    """Orchestrates all 8 demo pipeline stages in sequence."""

    def __init__(self, db: Session):
        self.db = db

    def run_full_pipeline(
        self,
        *,
        seed: int = 42,
        product_count: int = 50,
        store_count: int = 5,
        history_days: int = 730,
    ) -> DemoPipelineRun:
        """
        Execute all 8 pipeline stages. Returns the completed (or failed) run record.

        Stops immediately when any step fails. Does not retry or skip failed steps.
        """
        run_id = new_id()
        steps = [_step_record(n) for n in _STEP_NAMES]

        run = DemoPipelineRun(
            id=run_id,
            status="running",
            started_at=datetime.utcnow(),
            steps_json=steps,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        for i, name in enumerate(_STEP_NAMES):
            step = steps[i]
            step["status"] = "running"
            step["started_at"] = datetime.utcnow().isoformat()
            run.current_step = name
            run.steps_json = list(steps)
            self.db.commit()

            try:
                result_summary = self._run_step(
                    name,
                    seed=seed,
                    product_count=product_count,
                    store_count=store_count,
                    history_days=history_days,
                )
                step["status"] = "completed"
                step["completed_at"] = datetime.utcnow().isoformat()
                step["result_summary"] = result_summary
                logger.info("Demo pipeline step %s completed: %s", name, result_summary)

            except Exception as exc:
                step["status"] = "failed"
                step["completed_at"] = datetime.utcnow().isoformat()
                step["error_message"] = str(exc)
                logger.error("Demo pipeline step %s failed: %s", name, exc)

                # Mark all remaining steps as skipped
                for j in range(i + 1, len(_STEP_NAMES)):
                    steps[j]["status"] = "skipped"

                run.status = "failed"
                run.completed_at = datetime.utcnow()
                run.error_message = f"Step '{name}' failed: {exc}"
                run.steps_json = list(steps)
                run.current_step = name
                self.db.commit()
                self.db.refresh(run)
                return run

            run.steps_json = list(steps)
            self.db.commit()

        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.current_step = None
        run.steps_json = list(steps)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _run_step(
        self,
        name: str,
        *,
        seed: int,
        product_count: int,
        store_count: int,
        history_days: int,
    ) -> str:
        """Execute one pipeline step. Returns a short result summary string."""
        db = self.db

        if name == "reset_demo":
            from app.connectors.mock_commerce import MockCommerceConnector, MockConfig
            from app.services.ingestion_service import IngestionService

            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=history_days - 1)
            config = MockConfig(
                seed=seed,
                product_count=product_count,
                store_count=store_count,
                history_days=history_days,
                start_date=start_date,
                end_date=end_date,
            )
            connector = MockCommerceConnector(config)
            svc = IngestionService(connector, db)
            result = svc.reset_and_seed(start_date, end_date)
            counts = result.get("counts", {}) if isinstance(result, dict) else {}
            return f"Seeded {counts.get('orders', '?')} orders, {counts.get('inventory_snapshots', '?')} snapshots"

        if name == "aggregation":
            from app.services.aggregation_service import AggregationService

            row = db.query(func.min(RawOrder.order_date), func.max(RawOrder.order_date)).first()
            if not row or not row[0]:
                raise RuntimeError("No raw orders found — reset step may have failed")
            start, end = row[0], row[1]
            svc = AggregationService(db)
            result = svc.run_full_aggregation(start, end)
            counts = result.get("records_produced", {}) if isinstance(result, dict) else {}
            psd = counts.get("product_store_daily", "?")
            return f"Built product_store_daily: {psd} rows"

        if name == "features":
            from app.services.feature_service import FeatureService

            svc = FeatureService(db)
            result = svc.build_feature_matrix()
            rows = result.get("rows_created", "?") if isinstance(result, dict) else "?"
            return f"Built feature matrix: {rows} rows"

        if name == "baseline_forecast":
            from app.services.forecasting_service import ForecastingService

            svc = ForecastingService(db)
            result = svc.run_baseline_forecast(
                model_type="seasonal_naive",
                horizon_days=28,
                backtest_days=56,
            )
            rows = result.get("rows_created", "?") if isinstance(result, dict) else "?"
            return f"Baseline forecast: {rows} rows"

        if name == "train_ml":
            from app.services.training_service import TrainingService

            svc = TrainingService(db)
            result = svc.train_ml_forecaster(
                algorithm="hist_gradient_boosting",
                horizon_days=28,
                backtest_days=56,
            )
            rows = result.get("rows_created", "?") if isinstance(result, dict) else "?"
            return f"ML model trained: {rows} forecast rows"

        if name == "planning_forecast":
            from app.services.forecasting_service import ForecastingService

            svc = ForecastingService(db)
            result = svc.run_planning_forecast(
                model_type="seasonal_naive",
                horizon_days=28,
            )
            rows = result.get("rows_created", "?") if isinstance(result, dict) else "?"
            return f"Planning forecast: {rows} rows"

        if name == "stockout_risk":
            from app.services.stockout_service import StockoutService

            svc = StockoutService(db)
            result = svc.run_stockout_risk(
                horizon_days=28,
                mode="forward_planning",
            )
            rows = result.get("rows_created", "?") if isinstance(result, dict) else "?"
            return f"Stockout risk scored: {rows} rows"

        if name == "recommendations":
            from app.services.recommendation_service import RecommendationService

            svc = RecommendationService(db)
            result = svc.run_reorder_recommendations(include_low_risk=False)
            rows = result.get("rows_created", "?") if isinstance(result, dict) else "?"
            return f"Recommendations generated: {rows} rows"

        raise ValueError(f"Unknown pipeline step: {name}")

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_pipeline_runs(self, limit: int = 20) -> list[DemoPipelineRun]:
        return (
            self.db.query(DemoPipelineRun)
            .order_by(DemoPipelineRun.started_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_pipeline_run(self) -> DemoPipelineRun | None:
        return (
            self.db.query(DemoPipelineRun)
            .order_by(DemoPipelineRun.started_at.desc())
            .first()
        )
