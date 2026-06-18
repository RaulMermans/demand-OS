# DemandOS — Evaluation Plan

## 1. Data Generator Tests (Sprint 1)
- Generated products have valid SKUs, categories, costs, prices
- Generated stores have valid regions, channels
- Generated orders cover full date range with no gaps
- Generated order quantities are positive
- Generated inventory snapshots exist for every (product, store, week)
- No generated record contains derived ML fields
- Connector generates reproducible output given same seed

## 2. Validation Tests (Sprint 1)
- Invalid records (negative quantity, null external_id) are caught
- Future-dated orders trigger warnings
- Duplicate records are detected and logged
- Orphaned order lines (product_id not in raw_products) are flagged
- ValidationService emits PipelineEvents for each error class

## 3. Aggregation Tests (Sprint 2) ✅
- sales_daily totals match sum of fulfilled order lines for same (product, store, date)
- Cancelled/returned orders are excluded from sales_daily
- inventory_daily days_of_supply = on_hand / (rolling_7d_units / 7); NULL when no demand
- stockout_flag = True when on_hand_units == 0
- Promotion flags correctly joined (start_date ≤ date ≤ end_date, sku/store constraints)
- product_store_daily has exactly (n_products × n_stores × n_days) rows
- No forbidden ML fields in canonical tables
- AggregationRun record created per run with status=success and record counts
- Running aggregation twice produces identical row counts (idempotency)

## 4. Feature Engineering Tests (Sprint 3) ✅
- FeatureService builds feature_matrix from product_store_daily ✅
- One row per eligible (product, store, date) — no duplicates ✅
- lag_units_7d for date D = units_sold at D-7 in PSD ✅
- lag_units_1d for date D = units_sold at D-1 in PSD ✅
- rolling_units_mean_7d uses shift(1) — window ends at D-1, not D ✅
- rolling_units_mean_7d for D differs from target_units_sold in ≥ 90% of rows ✅
- rolling_units_std features exist and are non-negative ✅
- Calendar features correct (day_of_week=0 on Monday, is_weekend on Sat/Sun) ✅
- Promotion features populated (promo_active rows exist, discount_pct > 0 when active) ✅
- Price/margin features: retail_price > 0, gross_margin_pct in [0,1] ✅
- Price change features exist (0 for static-price connector; real values for dynamic pricing) ✅
- Inventory features: available_units ≥ 0, stockout_flag field present ✅
- Lifecycle: days_since_launch ≥ 0 for all rows (pre-launch excluded) ✅
- product_age_bucket values restricted to 4 valid buckets ✅
- Pre-launch rows (days_since_launch < 0) absent from feature_matrix ✅
- target_units_sold equals canonical sales_daily.units_sold for same key ✅
- No forbidden fields in feature_matrix schema (no forecast/risk/reorder columns) ✅
- Running build twice produces identical row count (idempotency) ✅
- POST /api/features/build returns completed status with rows_created ✅
- GET /api/features/status returns not_run / ready / failed correctly ✅
- GET /api/features/sample returns bounded rows with expected fields ✅
- /api/data-health includes feature_counts and latest_feature_run after build ✅
- FeatureRun record created with status, rows_created, date_min, date_max ✅

## 5. Forecasting Tests (Sprint 4) ✅

### Baseline models
- seasonal_naive runs without error on feature_matrix ✅
- moving_average_7d runs without error on feature_matrix ✅
- moving_average_28d runs without error on feature_matrix ✅
- Seasonal naive p50 = lag_units_7d (D-7 value) on deterministic fixture ✅
- Seasonal naive falls back to rolling_mean_7d when lag_7d is null ✅
- Moving average reads rolling_units_mean, not target_units_sold (no leakage) ✅

### Persistence
- Forecast rows persisted to forecasts table ✅
- Forecast rows include actual_units in backtest mode ✅
- ForecastRun record created with status=completed ✅
- Model metrics persisted to model_metrics table ✅

### Math correctness
- absolute_error = |actual - forecast| per row ✅
- squared_error = (actual - forecast)² per row ✅
- WAPE = sum(|a-f|) / sum(a); None when sum(actual)=0 ✅
- SMAPE: zero-denominator rows contribute 0 (no NaN/inf) ✅
- Bias = (sum(f)-sum(a)) / sum(a); None when sum(actual)=0 ✅

### Levels
- Metrics computed at overall level ✅
- Metrics computed at category level ✅
- Metrics computed at store level ✅

### Idempotency
- Re-running same model_type deletes prior run (clear-before-rewrite) ✅
- Only one completed run per model_type exists at any time ✅

### API
- POST /api/forecasts/baseline/run returns completed status + metrics ✅
- GET /api/forecasts/runs lists all runs ✅
- GET /api/forecasts/latest returns latest run + sample rows ✅
- GET /api/forecasts/product/{id} returns product-level actuals vs forecast ✅
- GET /api/model-metrics returns persisted metrics ✅
- /api/data-health includes forecast_counts + latest_forecast_run ✅

### Constraints
- No stockout/reorder/ML fields in Forecast or ModelMetric schema ✅
- WAPE/Bias return None (not 0 or inf) when denominator is zero ✅

## 6. ML Training Tests (Sprint 5) ✅

### CI / Repo Hygiene
- `.github/workflows/ci.yml` exists ✅
- `.github/dependabot.yml` exists ✅
- `.gitignore` protects model artifacts and generated data ✅
- Repo hygiene job blocks venv, pycache, node_modules, .env ✅

### ML Training
- TrainingService trains HistGradientBoosting from feature_matrix ✅
- Training uses only rows before backtest window (train_end < test_start) ✅
- target_units_sold and all forbidden fields excluded from features ✅
- Categorical encoding is deterministic (sorted categories) ✅
- Model artifact saved to models/forecasting/{model_version_id}.joblib ✅
- ModelVersion row persisted with status=completed ✅
- Forecast rows persisted for ML model ✅
- All p50 forecasts ≥ 0 ✅
- actual_units joined for backtest rows ✅
- ModelMetric rows persisted ✅
- Metrics at overall level ✅
- Metrics at category and store levels ✅
- Baseline comparison works when baseline runs exist ✅
- Baseline comparison graceful when no baselines ✅
- ML not forced to win: ml_won reflects actual WAPE comparison ✅
- Re-running same config is clear-before-rewrite safe ✅
- POST /api/models/train works ✅
- GET /api/models/versions works ✅
- GET /api/models/latest works ✅
- GET /api/models/compare works ✅
- /api/data-health includes model_counts after training ✅
- /api/overview includes honest ML readiness fields ✅
- No stockout/reorder tables populated in Sprint 5 ✅
- Existing Sprint 0–4 tests still pass ✅

## 7. Stockout / Reorder Tests (Sprint 6)
- Risk tier = critical when days_until_stockout ≤ lead_time_days
- Safety stock formula: Z × σ(demand) × √lead_time
- EOQ formula: sqrt(2 × D × S / H)
- Reorder point = avg_daily_demand × lead_time + safety_stock
- No reorder_recommendations row has recommended_qty ≤ 0
- Recommendations are not automatically submitted as purchase orders

## 7. API Contract Tests (Sprint 2+)
- /health returns {"status": "ok"}
- /api/overview returns well-formed JSON
- /api/forecasts returns list, each item has product_id, store_id, forecast_date, predicted_units
- /api/risks returns list, each item has risk_tier in {critical, high, medium, low}
- /api/recommendations returns list with recommended_qty, reorder_point, economic_order_qty

## 8. UI Smoke Tests (Sprint 4)
- All 6 routes return HTTP 200 (Next.js build check)
- No route shows hardcoded business metrics
- Scaffold banners visible when pipeline_ready=false

## 9. Replay / Idempotency Tests (Sprint 2)
- Running ingestion twice with same date range does not double-count records
- Running aggregation twice produces identical sales_daily rows
- Running feature service twice produces identical feature_matrix rows
- forecast_run with same model_version_id produces same predicted_units (deterministic)

## Test Framework
- Backend: pytest (apps/api/tests/)
- Frontend: Next.js type check (tsc --noEmit)
- Integration: scripts/verify.sh
