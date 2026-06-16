# DemandOS — ML Plan

## Forecast Objective

Predict daily unit demand per (product, store) combination for a 28-day horizon.
Minimum viable accuracy target: SMAPE < 25% on held-out test set.
Primary metric: WRMSSE (Weighted Root Mean Squared Scaled Error), aligned with M5 competition.

## Model Roadmap

### Phase A — Naive Baselines (Sprint 4a)
- Last-value carry-forward
- Seasonal naive: same weekday, 4 weeks ago
- 7-day moving average

### Phase B — Global ML Model (Sprint 4b)
- LightGBM trained across all (product, store) series simultaneously
- One model, N series — avoids sparse-data problem for low-volume SKUs
- Inspired by Nixtla/mlforecast global model approach

### Phase C — Prediction Intervals (Sprint 4c)
- Quantile regression: q=0.1, 0.9 (80% interval), q=0.05, 0.95 (90% interval)
- Conformal prediction as alternative (distribution-free coverage guarantee)

### Phase D — Deep Learning (Sprint 7, optional)
- N-BEATS or DLinear via unit8co/darts
- Compare against LightGBM baseline; adopt only if meaningful improvement

## Features (computed by FeatureService)

| Feature | Type | Description |
|---------|------|-------------|
| lag_7d | Lag | Units sold 7 days ago |
| lag_14d | Lag | Units sold 14 days ago |
| lag_28d | Lag | Units sold 28 days ago |
| rolling_mean_7d | Rolling | 7-day rolling average units |
| rolling_mean_14d | Rolling | 14-day rolling average units |
| rolling_mean_28d | Rolling | 28-day rolling average units |
| rolling_std_7d | Rolling | 7-day rolling std dev |
| day_of_week | Calendar | 0=Mon … 6=Sun |
| week_of_year | Calendar | 1–52 |
| month | Calendar | 1–12 |
| is_weekend | Calendar | Boolean |
| promotion_active | Promo | Boolean |
| discount_pct | Promo | Float 0–1 |
| days_since_last_promo | Promo | Integer |
| days_of_supply | Inventory | on_hand / avg_daily_demand |
| lead_time_days | Supplier | Nominal lead time |

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
