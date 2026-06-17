# DemandOS — ML Plan

## Forecast Objective

Predict daily unit demand per (product, store) combination for a 28-day horizon.
Minimum viable accuracy target: SMAPE < 25% on held-out test set.
Primary metric: WRMSSE (Weighted Root Mean Squared Scaled Error), aligned with M5 competition.

## Model Roadmap

### Phase A — Naive Baselines (Sprint 4) ✅
- Seasonal naive: forecast(D) = lag_units_7d [units sold D-7]; fallback chain documented
- 7-day moving average: forecast(D) = rolling_units_mean_7d [mean over D-7..D-1]
- 28-day moving average: forecast(D) = rolling_units_mean_28d [mean over D-28..D-1]
- All forecast signals read from leakage-safe feature_matrix
- Backtesting: last backtest_days of feature_matrix as test period (default 56 days)
- Metrics: MAE, RMSE, WAPE, SMAPE, Bias at overall/category/store levels
- Heuristic bands: p10 = max(0, p50 - σ), p90 = p50 + σ (±1 rolling std; documented heuristic)

### Phase B — Global ML Model (Sprint 5)
- LightGBM trained across all (product, store) series simultaneously
- One model, N series — avoids sparse-data problem for low-volume SKUs
- Inspired by Nixtla/mlforecast global model approach
- Evaluate against Sprint 4 baselines; adopt only if meaningful improvement

### Phase C — Prediction Intervals (Sprint 4c)
- Quantile regression: q=0.1, 0.9 (80% interval), q=0.05, 0.95 (90% interval)
- Conformal prediction as alternative (distribution-free coverage guarantee)

### Phase D — Deep Learning (Sprint 7, optional)
- N-BEATS or DLinear via unit8co/darts
- Compare against LightGBM baseline; adopt only if meaningful improvement

## Features — Sprint 3 (implemented in FeatureService)

All features are computed internally by `FeatureService.build_feature_matrix()`.
**Leakage-safe:** lag and rolling features use dates strictly before D (shift=1 before rolling).
**Pre-launch excluded:** rows where `days_since_launch < 0` are removed from the feature matrix.

| Feature | Column name | Type | Description |
|---------|------------|------|-------------|
| **Target** | `target_units_sold` | Float | Historical units sold on D (supervised label) |
| **Lag** | `lag_units_1d` | Float | Units sold 1 day ago |
| | `lag_units_7d` | Float | Units sold 7 days ago |
| | `lag_units_14d` | Float | Units sold 14 days ago |
| | `lag_units_28d` | Float | Units sold 28 days ago |
| **Rolling mean** | `rolling_units_mean_7d` | Float | Mean units over [D-7..D-1] |
| | `rolling_units_mean_14d` | Float | Mean units over [D-14..D-1] |
| | `rolling_units_mean_28d` | Float | Mean units over [D-28..D-1] |
| | `rolling_revenue_mean_7d` | Float | Mean revenue over [D-7..D-1] |
| | `rolling_revenue_mean_28d` | Float | Mean revenue over [D-28..D-1] |
| **Rolling std** | `rolling_units_std_7d` | Float | Std dev units over [D-7..D-1] |
| | `rolling_units_std_28d` | Float | Std dev units over [D-28..D-1] |
| **Calendar** | `day_of_week` | Int | 0=Mon … 6=Sun |
| | `week_of_year` | Int | 1–53 |
| | `month` | Int | 1–12 |
| | `quarter` | Int | 1–4 |
| | `is_weekend` | Bool | True for Sat/Sun |
| **Promotion** | `promo_active` | Bool | Active promotion on D |
| | `discount_pct` | Float | Highest discount in effect (0 if none) |
| **Price/margin** | `retail_price` | Float | Product unit price |
| | `unit_cost` | Float | Product unit cost |
| | `gross_margin_pct` | Float | (price - cost) / price |
| | `price_change_pct_7d` | Float | Price change vs 7 days ago |
| | `price_change_pct_28d` | Float | Price change vs 28 days ago |
| **Inventory** | `available_units` | Float | On-hand inventory on D |
| | `stockout_flag` | Bool | True if on_hand = 0 |
| | `days_of_supply` | Float | on_hand / recent_demand_rate |
| **Lifecycle** | `days_since_launch` | Int | Days since product launch (≥ 0) |
| | `product_age_bucket` | Str | new_0_30 / ramp_31_90 / mature_91_365 / established_365_plus |

**Implementation notes:**
- `rolling(W, min_periods=1).mean()` applied AFTER `shift(1)` — window covers [D-W .. D-1]
- Static prices in MockConnector → `price_change_pct_*` = 0 always; real connectors with dynamic pricing get actual values
- `days_since_last_promo` deferred to Sprint 4 (requires looking back from each date)
- `lead_time_days` deferred to Sprint 5 (required for reorder point calculation)

## Cross-Validation Strategy

Walk-forward time-series CV with expanding window:
- Minimum 12 months of history required before first CV fold
- Hold out last 28 days as final test set (never used for hyperparameter tuning)
- Reference: M5 competition 28-day evaluation horizon

## Evaluation Metrics

| Metric | Description |
|--------|-------------|
| RMSE | Root Mean Squared Error |
| MAE | Mean Absolute Error |
| SMAPE | Symmetric MAPE (handles zeros) |
| WRMSSE | Weighted RMSE Scaled — M5 primary metric |
| Bias | Mean signed error (over/under-forecast detection) |
| Coverage | % actuals within prediction interval |

## References

- Nixtla/mlforecast: global ML forecasting, feature engineering, cross-validation
- Mcompetitions/M5-methods: retail demand, 28-day horizon, WRMSSE metric
- unit8co/darts: optional later for model comparison
