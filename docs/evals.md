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

## 3. Aggregation Tests (Sprint 2)
- sales_daily totals match sum of order lines for same (product, store, date)
- Cancelled/returned orders are excluded from sales_daily
- inventory_daily days_of_supply = on_hand / rolling_mean_7d demand
- Promotion flags are correctly joined
- No days are skipped in date range

## 4. Feature Engineering Tests (Sprint 3)
- lag_7d for date D = total_units on D-7
- rolling_mean_7d for date D = mean of D-6 through D
- Calendar features are correct (day_of_week, is_weekend, etc.)
- Features are computed only from data prior to the feature date (no leakage)
- Feature matrix has no NaN for warmup window rows (handled with fill strategy)

## 5. Forecasting Tests (Sprint 4)
- Model trains without error on feature matrix
- Forecast output covers all (product, store) pairs
- Forecast horizon is exactly 28 days
- Lower bound ≤ predicted_units ≤ upper bound
- SMAPE on CV fold is logged to model_metrics
- Naive baseline beats trivially-wrong model (sanity check)

## 6. Stockout / Reorder Tests (Sprint 5)
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
