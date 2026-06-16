"""
FeatureService — engineers time-series features for ML from aggregated data.

Input:  sales_daily, inventory_daily, raw_promotions (from DB)
Output: feature_matrix table

Features planned (Sprint 3):
  Lag features:        lag_7d, lag_14d, lag_28d (units sold N days ago)
  Rolling windows:     rolling_mean_7d/14d/28d, rolling_std_7d/14d
  Calendar:            day_of_week, week_of_year, month, is_weekend, is_holiday
  Promotion:           promotion_active, discount_pct, days_since_last_promo
  Inventory:           days_of_supply, on_order_qty
  Supplier:            lead_time_days (from raw_suppliers via product join)
  Cross-product:       category_mean_7d (optional, Sprint 4)

Reference: Nixtla/mlforecast feature engineering patterns for scalable ML forecasting.

These features are NEVER inputs to the system — they are only computed outputs.
"""


class FeatureService:
    def run(self, start_date=None, end_date=None) -> dict:
        """
        Scaffold: returns not-implemented status.
        Sprint 3 TODO: implement feature engineering pipeline.
        """
        return {
            "status": "scaffold_ready",
            "message": "FeatureService not yet implemented — Sprint 3.",
            "features_computed": 0,
        }
