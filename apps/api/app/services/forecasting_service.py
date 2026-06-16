"""
ForecastingService — trains and runs demand forecasting models.

Input:  feature_matrix (from DB)
Output: forecasts table (predicted_units + confidence intervals)

Model plan (Sprint 4):
  Phase A — Baseline:      Naive seasonal (last-year same-week), moving average
  Phase B — ML:            LightGBM global model trained across all SKU/store series
  Phase C — Deep learning: Optional DLinear or N-BEATS via darts (Sprint 6+)

Forecast horizon: 28 days (aligned with M5 competition framing).
Cross-validation:  walk-forward time-series CV with expanding window.
Prediction intervals: quantile regression (q=0.1, 0.9) or conformal prediction.

Reference: Nixtla/mlforecast for global ML forecasting approach.
           Mcompetitions/M5-methods for 28-day retail horizon and WRMSSE metric.
"""


class ForecastingService:
    def run_forecast(self, horizon_days: int = 28) -> dict:
        """
        Scaffold: returns not-implemented status.
        Sprint 4 TODO: train baseline model and produce forecasts.
        """
        return {
            "status": "scaffold_ready",
            "message": "ForecastingService not yet implemented — Sprint 4.",
            "forecasts_produced": 0,
            "horizon_days": horizon_days,
        }
