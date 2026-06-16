"""
EvaluationService — computes model accuracy metrics after actuals are available.

Input:  forecasts (for a past horizon), sales_daily (actuals)
Output: model_metrics table

Metrics planned (Sprint 6):
  - RMSE  (Root Mean Squared Error)
  - MAE   (Mean Absolute Error)
  - SMAPE (Symmetric MAPE — handles zero actuals)
  - WRMSSE (Weighted RMSE Scaled — M5 competition primary metric)
  - Bias  (mean signed error — detects systematic over/under-forecasting)
  - Coverage (% actuals within prediction interval)

Evaluation is run per: model_version, product, store, horizon.

Reference: Mcompetitions/M5-methods for WRMSSE metric definition.
"""


class EvaluationService:
    def evaluate(self, forecast_run_id: str) -> dict:
        """
        Scaffold: returns not-implemented status.
        Sprint 6 TODO: implement evaluation against actuals.
        """
        return {
            "status": "scaffold_ready",
            "message": "EvaluationService not yet implemented — Sprint 6.",
            "metrics_computed": 0,
            "forecast_run_id": forecast_run_id,
        }
