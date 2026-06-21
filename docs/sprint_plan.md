# DemandOS — Sprint Plan

## Sprint 0 — Scaffold ✅
- [x] Monorepo structure
- [x] FastAPI backend skeleton
- [x] Connector base class + stubs
- [x] Raw Pydantic schemas
- [x] SQLAlchemy ORM models (all layers)
- [x] Next.js dashboard shell (6 routes)
- [x] Pytest tests (health, connector contract, raw data rule)
- [x] Root documentation (README, CLAUDE.md, AGENTS.md, DESIGN.md, etc.)
- [x] docker-compose.yml with Postgres
- [x] Scripts placeholders

## Sprint 1 — Raw Synthetic Commerce Data Generator ✅ (Current)
- [x] Implement MockCommerceConnector with realistic synthetic data:
  - 50 products across 5 categories (Tops, Bottoms, Footwear, Accessories, Outerwear)
  - 3 product tiers: bestseller (20%), standard (60%), slow_mover (20%)
  - 5 stores: Online, Madrid Flagship, Barcelona Store, Outlet, Wholesale
  - 10 suppliers with realistic lead times and reliability scores
  - 730 days of daily order-line history
  - Weekday/weekend patterns + monthly/seasonal demand multipliers
  - 8–11 promotional events per year with discount-driven uplift
  - Daily inventory snapshots with real stockout events
  - Purchase order history driven by internal reorder logic
- [x] Implement IngestionService — bulk-persist all raw record types
- [x] Implement ValidationService — referential integrity + date checks + field guard
- [x] Activate /api/data-health with real persisted counts
- [x] Add POST /api/demo/reset — seed or re-seed demo dataset
- [x] Add POST /api/ingestion/run and GET /api/ingestion/runs
- [x] Implement scripts/seed_demo_data.py (--seed, --products, --stores, --days)
- [x] Implement scripts/run_daily_ingestion.py (--date, --dry-run)
- [x] Add tests: test_mock_connector.py, test_ingestion.py, test_data_health.py

**Counts generated (seed=42, 50 products, 5 stores, 730 days):**
- Products: 50
- Stores: 5
- Suppliers: 10
- Promotions: ~40–50 (8–11/year × 2 years, filtered to window)
- Order lines: ~80k–150k
- Inventory snapshots: ~182,500 (50 × 5 × 730)
- Purchase orders: ~3,000

**Limitations (to address in Sprint 2):**
- Daily append mode is idempotent but regenerates the full dataset each time
- No aggregated daily sales tables yet (Sprint 2)
- AggregationService not yet called after ingestion

## Sprint 2 — Aggregation Pipeline ✅ (Current)
- [x] Implement AggregationService with `run_full_aggregation(start_date, end_date)`:
  - Cleaned layer: orders_clean, inventory_clean, promotions_clean, products_clean,
    stores_clean, suppliers_clean, purchase_orders_clean (audit trail)
  - sales_daily: sum fulfilled orders per (product, store, date); excludes cancelled/returned
  - inventory_daily: latest snapshot per (product, store, date); days_of_supply = on_hand / rolling_mean_7d
  - promotion_daily: active flag per (product, store, date) from raw_promotions
  - product_store_daily: denormalized daily fact joining all three tables
- [x] Add POST /api/aggregation/run and GET /api/aggregation/status endpoints
- [x] Update /api/data-health with canonical_counts and latest_aggregation_run
- [x] Add scripts/build_canonical_tables.py (CLI with --start, --end, --dry-run)
- [x] Update scripts/verify.sh with Sprint 2 file checks
- [x] Add tests/test_aggregation.py — 20 tests covering:
  - Reconciliation, excluded statuses, days_of_supply formula, promo flags
  - Idempotency, product_store_daily completeness, forbidden fields
  - AggregationRun record, API endpoints, data-health canonical counts

**Counts produced (seed=42, 50 products, 5 stores, 730 days):**
- orders_clean: ~120k–130k (fulfilled + pending)
- inventory_clean: ~182,500
- sales_daily: ~50k–80k rows (days with at least one sale per product/store)
- inventory_daily: ~182,500 rows
- promotion_daily: 182,500 rows (50 × 5 × 730)
- product_store_daily: 182,500 rows (complete cartesian product)

**Limitations (to address in Sprint 3):**
- days_of_supply uses simple 7-day rolling mean; Sprint 3 FeatureService computes richer features
- product_store_daily includes all product/store/date triples even for inactive combinations
- No automated trigger of aggregation after ingestion (manual via API or script)

## Sprint 3 — Feature Engineering ✅
- [x] Implement `FeatureService.build_feature_matrix()` — full pandas-based pipeline:
  - Lag features: lag_units_1d, 7d, 14d, 28d (shift before use; all leakage-safe)
  - Rolling features: rolling_units_mean_7d/14d/28d, rolling_units_std_7d/28d, rolling_revenue_mean_7d/28d
    (shift(1) before rolling ensures window ends at D-1)
  - Calendar features: day_of_week (0=Mon), week_of_year, month, quarter, is_weekend
  - Promotion features: promo_active, discount_pct (from canonical promotion_daily)
  - Price/margin features: retail_price, unit_cost, gross_margin_pct, price_change_pct_7d/28d
  - Inventory features: available_units, stockout_flag, days_of_supply (from inventory_daily)
  - Lifecycle features: days_since_launch, product_age_bucket (new_0_30/ramp_31_90/mature_91_365/established_365_plus)
  - target_units_sold: historical label from product_store_daily (NOT a forecast)
- [x] Add FeatureRun tracking table and FeatureMatrix table with 36 individual columns
- [x] Pre-launch rows (days_since_launch < 0) excluded from feature_matrix
- [x] Forbidden fields enforced: no forecast, risk_score, reorder_quantity, etc.
- [x] Full rebuild idempotency: DELETE ALL before reinsert
- [x] Add `POST /api/features/build`, `GET /api/features/status`, `GET /api/features/sample`
- [x] Update `/api/data-health` with `feature_counts` and `latest_feature_run`
- [x] Update `/api/overview` with `feature_rows_count` and `feature_readiness`
- [x] Add `scripts/build_features.py` CLI (--max-lag-days, --dry-run)
- [x] Update `scripts/verify.sh` with Sprint 3 file checks
- [x] Add `tests/test_features.py` — 27 tests covering:
  - Feature build from PSD, no duplicates, lag correctness (1d, 7d)
  - Rolling mean leakage-safety (PSD-based comparison + statistical leakage rate)
  - Rolling std existence, calendar correctness (Monday=0, weekend flag)
  - Promotion features, price/margin features, inventory features, lifecycle features
  - Pre-launch exclusion, target_units_sold accuracy, forbidden fields schema check
  - Idempotency, API endpoints (build, status, sample), data-health counts, FeatureRun record

**Counts produced (seed=42, 4 products, 2 stores, 70 days):**
- feature_matrix rows: ~560 eligible rows (full cartesian minus pre-launch)
- FeatureRun: 1 record per build call

**Leakage-safety approach (documented here):**
- All lag and rolling features use dates STRICTLY before D (shift=1 before rolling)
- Pre-launch rows are EXCLUDED (not marked) so no rows with days_since_launch < 0 appear in training data
- target_units_sold is the supervised learning label (historical, not future)
- Static prices in MockConnector → price_change_pct = 0; field exists for real connectors

**Limitations (to address in Sprint 4):**
- No ML model training yet; feature_matrix is ready but unused by forecasting
- price_change_pct always 0 for MockConnector (static prices)
- No automated trigger of feature build after aggregation (manual via API or script)

## Sprint 4 — Baseline Forecasting + Backtesting ✅
- [x] Implement `ForecastingService.run_baseline_forecast()` reading from `feature_matrix`
- [x] Seasonal naive model: forecast(D) = lag_units_7d (D-7); fallback chain: rolling_mean_7d → rolling_mean_28d → 0
- [x] Moving average 7d model: forecast(D) = rolling_units_mean_7d
- [x] Moving average 28d model: forecast(D) = rolling_units_mean_28d
- [x] Heuristic p10/p90 bands: ±1σ of recent demand (documented as heuristics, not probabilistic)
- [x] Historical backtest window (last `backtest_days` of feature_matrix)
- [x] Per-row errors: absolute_error, squared_error, absolute_percentage_error (SMAPE component)
- [x] Aggregate metrics: MAE, RMSE, WAPE, SMAPE, Bias at overall / category / store levels
- [x] WAPE/Bias safely handle zero denominators (return None)
- [x] SMAPE safely handles zero-denominator rows (contribute 0)
- [x] Persist forecasts, model_metrics, forecast_runs to DB
- [x] Clear-before-rewrite idempotency: re-running same model_type deletes prior run
- [x] Redesigned ForecastRun, Forecast, ModelMetric ORM models for Sprint 4 schema
- [x] Add `POST /api/forecasts/baseline/run`, `GET /api/forecasts/runs`, `GET /api/forecasts/latest`
- [x] Add `GET /api/forecasts/product/{product_id}`, `GET /api/model-metrics`
- [x] Update `/api/data-health` with `forecast_counts` and `latest_forecast_run`
- [x] Update `/api/overview` with honest baseline forecasting readiness metrics
- [x] Add `scripts/run_baseline_forecast.py` (--model, --horizon-days, --backtest-days, --dry-run)
- [x] Update `scripts/verify.sh` with Sprint 4 file checks
- [x] Add `tests/test_forecasting.py` — 31 tests covering all Sprint 4 requirements
- [x] No LightGBM, no ML model training, no stockout risk, no reorder recommendations

**Counts produced (seed=42, 4 products, 2 stores, 91 days, backtest_days=28):**
- forecast_runs: 1 per model type
- forecasts: ~224 rows (4 × 2 × 28 days, minus pre-launch)
- model_metrics: overall + per-category + per-store rows

**Baseline model performance (indicative, depends on seed and data):**
- Seasonal naive WAPE: typically 0.25–0.55 on retail mock data
- Moving average 7d WAPE: typically 0.25–0.50
- Moving average 28d WAPE: typically 0.30–0.60

**Limitations (to address in Sprint 5):**
- No ML model training; baselines are rule-based
- p10/p90 are ±1σ heuristics, not true probabilistic intervals
- No stockout risk scoring yet (Sprint 5)
- No reorder recommendations yet (Sprint 5)

## Sprint 5 — ML Forecasting Model + Model Registry + CI ✅
- [x] GitHub Actions CI with backend, frontend, and repo-hygiene jobs
- [x] Dependabot config for GitHub Actions, pip, and npm
- [x] `.gitignore` updated to protect model artifacts and generated data
- [x] `scikit-learn` + `joblib` added to pyproject.toml
- [x] `ModelVersion` ORM expanded with full registry fields (algorithm, status, dates, feature_columns_json, etc.)
- [x] `TrainingService.train_ml_forecaster()` implemented:
  - HistGradientBoostingRegressor (scikit-learn) across all (product, store) series
  - 30 leakage-safe features (27 numeric + 3 categorical)
  - OrdinalEncoder with sorted categories for deterministic encoding
  - Train/test split by date; test = last backtest_days of feature_matrix
  - Predictions clipped at 0; heuristic ±1σ p10/p90 bands
  - Model artifact saved to `models/forecasting/{model_version_id}.joblib`
  - Baseline comparison (honest: ML not forced to win)
  - Clear-before-rewrite idempotency
- [x] `POST /api/models/train` — trains and returns result + baseline comparison
- [x] `GET /api/models/versions` — model registry list
- [x] `GET /api/models/latest` — latest completed ML model
- [x] `GET /api/models/compare` — baseline vs ML comparison
- [x] `/api/data-health` updated with `model_counts` and `latest_model_version`
- [x] `/api/overview` updated with honest ML readiness fields
- [x] `scripts/train_model.py` — CLI for training
- [x] `scripts/verify.sh` updated with Sprint 5 file checks
- [x] `tests/test_training.py` — 27 tests covering all Sprint 5 requirements
- [x] No stockout risk or reorder recommendation logic introduced

**Model performance (seed=42, 4 products, 2 stores, 91 days, backtest_days=28):**
- HistGradientBoosting WAPE: varies with data; compared honestly against baselines
- Seasonal naive WAPE (reference): typically 0.25–0.55 on retail mock data

**Counts produced:**
- model_versions: 1 per training run
- forecast_runs: 1 per training run (model_type="hist_gradient_boosting")
- forecasts: ~224 rows (4 × 2 × 28 days)
- model_metrics: overall + per-category + per-store rows

**CI jobs:**
- `backend`: Python 3.11, pytest, verify.sh
- `frontend`: Node LTS, `npm run build` (type-check + production bundle)
- `repo-hygiene`: no .env, no node_modules/venv/pycache, no model artifacts, no secret files

**Feature engineering (30 features):**
- 27 numeric: lag_units (1d/7d/14d/28d), rolling mean/std (7d/14d/28d), rolling revenue, calendar (6), promo (2), price/margin (7), inventory (3), days_since_launch
- 3 categorical (OrdinalEncoder, sorted): category, store_channel, product_age_bucket
- target_units_sold is label only — never an input feature

**Limitations (to address in Sprint 6):**
- No stockout risk scoring yet
- p10/p90 are ±1σ heuristics, not calibrated probabilistic intervals
- No model monitoring or drift detection

## Sprint 6 — Stockout Risk Engine ✅
- [x] `StockoutRiskRun` table: full audit record per risk engine execution
- [x] `StockoutRisk` table: expanded Sprint 6 schema per (risk_run × product × store)
- [x] `ForecastRun.mode` column added: `backtest` / `forward_planning`
- [x] `ForecastingService.run_planning_forecast()`: forward-looking baseline forecasts
- [x] `POST /api/forecasts/planning/run`: generate future forecast rows (mode=forward_planning)
- [x] `StockoutService.run_stockout_risk()`: full implementation:
  - Forward planning mode: uses forward_planning forecast + latest inventory_daily
  - Historical simulation mode: uses backtest forecast + backtest start date
  - Current inventory from latest `inventory_daily` on/before as_of_date
  - Inbound POs (status: submitted/confirmed) within [as_of_date+1, as_of_date+horizon]
  - Supplier lead time from `raw_suppliers.lead_time_days_max`
  - Forecast demand: sum(p50_units), sum(p90_units with null→p50 fallback) over horizon
  - Projected end inventory (p50 and p90), average daily forecast, days of supply
  - Days until stockout (null when no projected stockout within horizon)
  - Safety stock: 1.65 × rolling_std_7d × √lead_time (from feature_matrix last row)
  - Inventory coverage ratio, lost sales units/value estimate
  - Risk tier: critical / high / medium / low / unknown (deterministic rules)
  - Risk score: 0–100 numeric (base by tier + supplier reliability + lost sales adjustments)
  - Idempotency: clear-before-rewrite for same (mode, horizon, as_of_date)
- [x] `POST /api/risks/run`, `GET /api/risks/runs`, `GET /api/risks/latest`
- [x] `GET /api/risks` (ranked, filtered by tier/store/category)
- [x] `GET /api/risks/product/{product_id}` (risk per store for one product)
- [x] `/api/data-health` updated with `risk_counts` and `latest_stockout_risk_run`
- [x] `/api/overview` updated with honest risk metrics (no hardcoded values):
  - `critical_stockout_count`, `high_stockout_count`, `medium_stockout_count`, `low_stockout_count`
  - `estimated_lost_sales_value`, `latest_risk_run_status`, `latest_risk_horizon_days`
- [x] `scripts/run_planning_forecast.py` (--model, --horizon-days, --dry-run)
- [x] `scripts/run_stockout_risk.py` (--horizon-days, --forecast-run-id, --mode, --dry-run)
- [x] `scripts/verify.sh` updated with Sprint 6 file checks
- [x] `tests/test_stockout.py` — 35 tests (all passing):
  - Formula correctness (p50 sum, p90 fallback, days-of-supply, projected inventory)
  - Safety stock formula verification
  - Lost sales units and value formulas
  - All 5 risk tier triggers (critical/high/medium/low/unknown)
  - Risk score bounded 0–100
  - Inbound PO horizon inclusion/exclusion
  - Supplier lead time join
  - Idempotency / clear-before-rewrite
  - Forward planning mode errors without usable forecast
  - API endpoints (run, latest, list, product)
  - Data-health and overview honest metric inclusion
  - No reorder recommendation fields
  - No reorder recommendations in ReorderRecommendation table
- [x] No reorder recommendations implemented (Sprint 7)

**Counts produced (seed=42, 4 products, 2 stores, 91 days, horizon=28):**
- stockout_risk_runs: 1 per risk run call
- stockout_risks: up to (products × stores) rows per run

**Risk tier breakdown (indicative, depends on inventory levels and forecasts):**
- critical: products/stores where demand within lead-time window exceeds available stock
- high: projected p50 end inventory negative, or coverage ratio < 1.0
- medium: p90 projection below safety stock, or thin coverage ratio
- low: well-covered inventory with safety buffer

**Limitations (to address in Sprint 7):**
- Planning forecast is a flat (constant) projection — no ML future inference yet
- No reorder quantities or EOQ calculations yet (Sprint 7)
- Safety stock formula uses rolling_units_std_7d as demand_std_daily (reasonable for weekly data)

## Sprint 7 — Reorder Recommendation Engine ✅
- [x] `RecommendationRun` table: audit record per recommendation engine execution
- [x] `ReorderRecommendation` table: full Sprint 7 schema per (rec_run × product × store)
- [x] `RecommendationService.run_reorder_recommendations()` — full implementation:
  - Selects latest completed forward_planning stockout risk run (or specific run_id)
  - Reads stockout_risk rows; filters low-risk rows by default
  - Joins product info (unit_cost, unit_price) from raw_products
  - Computes inventory_position = available + inbound
  - Computes lead_time_demand = average_daily_forecast × lead_time_days
  - Computes reorder_point = lead_time_demand + safety_stock_units
  - Computes recommended_units = max(0, reorder_point - inventory_position)
  - Rounds recommended_units_rounded to order_multiple (default 1)
  - Applies min_order_quantity constraint (default 1)
  - Computes estimated_order_cost = recommended_units_rounded × unit_cost
  - Computes estimated_lost_sales_avoided = min(lost_sales_value, rounded × unit_price)
  - Assigns urgency via deterministic rules (critical/high/medium/low)
  - Generates template-based recommendation_reason (no LLM)
  - Assigns confidence_level from data completeness (high/medium/low/unknown)
  - Idempotency: clear-before-rewrite for same source_risk_run_id
- [x] `POST /api/recommendations/run` — generate recommendations
- [x] `GET /api/recommendations/runs` — list all recommendation runs
- [x] `GET /api/recommendations/latest` — latest completed run + ranked rows
- [x] `GET /api/recommendations` — ranked/filtered list (urgency, status, tier, store, category)
- [x] `GET /api/recommendations/product/{product_id}` — per-product recommendations
- [x] `PATCH /api/recommendations/{id}/status` — status workflow (no purchase orders)
- [x] `/api/data-health` updated with `recommendation_counts` and `latest_recommendation_run`
- [x] `/api/overview` updated with honest recommendation metrics:
  - open_recommendation_count, critical_recommendation_count, high_recommendation_count
  - total_recommended_units, estimated_order_cost, estimated_lost_sales_avoided
  - latest_recommendation_run_status
- [x] `scripts/run_recommendations.py` (--risk-run-id, --include-low-risk, --dry-run)
- [x] `scripts/verify.sh` updated with Sprint 7 file checks
- [x] `tests/test_recommendations.py` — 41 tests covering all Sprint 7 requirements
- [x] No real purchase orders, no external API calls, no email/Slack

**Formulas implemented:**
- `inventory_position = current_available_units + inbound_units_within_horizon`
- `lead_time_demand = average_daily_forecast × supplier_lead_time_days`
- `reorder_point = lead_time_demand + safety_stock_units`
- `recommended_units = max(0, reorder_point - inventory_position)`
- `recommended_units_rounded = ceil(raw / order_multiple) × order_multiple`
  clamped to min_order_quantity when recommended_units > 0
- `estimated_order_cost = recommended_units_rounded × unit_cost`
- `estimated_lost_sales_avoided = min(lost_sales_value_estimate, rounded × unit_price)`

**Urgency rules (deterministic):**
- critical: risk_tier=critical OR days_until_stockout <= 7
- high: risk_tier=high OR days_until_stockout <= supplier_lead_time_days
- medium: risk_tier=medium OR recommended_units_rounded > 0
- low: otherwise

**Status workflow:** open → reviewed → approved_internal / ignored / resolved
approved_internal = approved inside DemandOS only; no external action taken.

**Counts produced (seed=42, 4 products, 2 stores, 91 days, horizon=28):**
- recommendation_runs: 1 per run call
- reorder_recommendations: up to products × stores non-low-risk rows

**Limitations (to address in Sprint 8):**
- Min order quantity and order multiple defaults to 1 (no supplier constraint table yet)
- Flat forward-planning forecast used; ML future inference not yet implemented
- No dashboard pages connected to real recommendation data yet

## Sprint 8 — Backend API Hardening + Dashboard Data Contracts ✅
- [x] Stabilize all API response contracts with typed Pydantic schemas (`apps/api/app/schemas/api.py`)
- [x] Add typed frontend API client (`apps/web/lib/api.ts` + `apps/web/lib/types.ts`)
- [x] Connect all dashboard pages to real backend data (no hardcoded values)
- [x] Add `/recommendations` dashboard page
- [x] Add Alembic migration support (alembic.ini, env.py, script.py.mako, initial migration)
- [x] Add 5 dashboard summary endpoints (GET /api/dashboard/*)
- [x] Add offset pagination to recommendations and risks list endpoints
- [x] Add reusable UX components: LoadingState, ErrorState, EmptyState, StatusBadge, DataTable
- [x] Add 46 new tests (test_api_contracts.py + test_alembic.py)
- [x] 295 backend tests passing; Next.js build passes; TypeScript compiles
- [x] No new business logic introduced

**Sprint 8 local demo commands:**
```bash
uvicorn app.main:app --reload  # port 8000
curl -X POST http://localhost:8000/api/demo/reset
curl -X POST http://localhost:8000/api/aggregation/run
curl -X POST http://localhost:8000/api/features/build
curl -X POST http://localhost:8000/api/forecasts/baseline/run
curl -X POST http://localhost:8000/api/models/train
curl -X POST http://localhost:8000/api/forecasts/planning/run
curl -X POST http://localhost:8000/api/risks/run
curl -X POST http://localhost:8000/api/recommendations/run
cd apps/web && npm run dev  # port 3000
```

## Sprint 9 — Dashboard UX + Safe Pipeline Controls + API Key Guard ✅
- [x] Charts on Overview, Forecasts, Risks, and Recommendations pages (recharts)
- [x] `KpiCard`, `ChartCard`, `BarChartPanel`, `LineChartPanel` components
- [x] `PipelineControlButton`, `ApiKeyInput` components
- [x] `/pipeline` page — safe manual controls for every pipeline stage
- [x] "Run Full Demo Pipeline" button (sequential, stops on first failure, confirm before reset)
- [x] Product forecast drilldown embedded in `/forecasts` (product ID input + line chart)
- [x] `DEMANDOS_API_KEY` env var guard on all POST/PATCH write endpoints
- [x] Disabled by default (local dev works without key)
- [x] API key stored in sessionStorage only (not localStorage, not env)
- [x] `GET /api/dashboard/pipeline-status` — per-step readiness for 8 pipeline stages
- [x] `GET /api/dashboard/product/{product_id}` — read-only product drilldown
- [x] `GET /api/dashboard/pipeline-status` used on Overview and Pipeline pages
- [x] 26 new backend tests (`test_api_key_guard.py`) — 321 total, all passing
- [x] TypeScript clean, Next.js build passing
- [x] `scripts/verify.sh` updated with Sprint 9 checks
- [x] No new ML/risk/recommendation formulas
- [x] No external side effects

**Sprint 9 local demo commands:**
```bash
# Backend
uvicorn app.main:app --reload  # port 8000

# Run demo via UI (go to /pipeline)
# Or via curl:
curl -X POST http://localhost:8000/api/demo/reset
curl -X POST http://localhost:8000/api/aggregation/run
curl -X POST http://localhost:8000/api/features/build
curl -X POST http://localhost:8000/api/forecasts/baseline/run
curl -X POST http://localhost:8000/api/models/train
curl -X POST http://localhost:8000/api/forecasts/planning/run
curl -X POST http://localhost:8000/api/risks/run
curl -X POST http://localhost:8000/api/recommendations/run

# Frontend
cd apps/web && npm run dev  # port 3000
# Pages: / /overview /forecasts /risks /recommendations /model-performance /data-health /pipeline
```

**API Key Guard usage:**
```bash
# Set key in .env (never commit):
DEMANDOS_API_KEY=your-secret-key

# Call with key:
curl -X POST http://localhost:8000/api/aggregation/run \
  -H "X-DemandOS-API-Key: your-secret-key"

# In the UI: go to /pipeline, enter the key in the API Key field, then run pipeline steps.
```

## Sprint 10 — End-to-End Demo Flow + UX Polish + Vercel Deployment Setup ✅
- [x] `DemoPipelineService` orchestrates all 8 pipeline stages in sequence
- [x] `DemoPipelineRun` table: durable run record with per-step status
- [x] `POST /api/demo/run-full-pipeline` — full pipeline in one call (API-key protected)
- [x] `GET /api/demo/pipeline-runs` — list all pipeline run records
- [x] `GET /api/demo/pipeline-runs/latest` — latest run with step breakdown
- [x] `/pipeline` page updated: durable run panel, step links to dashboard pages
- [x] `/products/[productId]` page: product drilldown with forecast chart + risk + recommendations
- [x] `apps/web/vercel.json` — Vercel-ready configuration
- [x] `apps/web/.env.example` — `NEXT_PUBLIC_API_BASE_URL` documented
- [x] `apps/api/.env.example` — `DEMANDOS_API_KEY` documented
- [x] `docs/demo_runbook.md` — step-by-step demo guide
- [x] `docs/operator_runbook.md` — operator guide (reset, API key, safety guarantees)
- [x] `docs/deployment.md` — Vercel frontend + backend deployment docs
- [x] `docs/screenshots/README.md` — portfolio screenshot guide
- [x] 13 new backend tests (`test_demo_pipeline.py`) — 334 total, all passing
- [x] TypeScript clean, Next.js build passing
- [x] `scripts/verify.sh` updated with Sprint 10 checks (112/112 passing)
- [x] No new ML/risk/recommendation formulas introduced
- [x] No external side effects

**Sprint 10 local demo commands:**
```bash
# Backend
uvicorn app.main:app --reload  # port 8000

# Full pipeline via UI:
# Go to http://localhost:3000/pipeline → Run Full Demo Pipeline

# Full pipeline via API:
curl -X POST http://localhost:8000/api/demo/run-full-pipeline
curl http://localhost:8000/api/demo/pipeline-runs/latest

# Frontend
cd apps/web && npm run dev  # port 3000

# Pages: / /overview /forecasts /risks /recommendations /model-performance /data-health /pipeline /products/{id}
```

**Vercel deployment (frontend only):**
```bash
cd apps/web
vercel         # preview
vercel --prod  # production
# Set NEXT_PUBLIC_API_BASE_URL in Vercel environment variables
```

## Sprint 10B — Single Vercel Project Adapter ✅
- [x] `vercel.json` at repo root — routes `/api/*` to Python function, `/*` to Next.js
- [x] `api/index.py` — FastAPI adapter (imports `app.main.app` via sys.path)
- [x] `api/__init__.py` — makes `api` a Python package for test imports
- [x] `requirements.txt` at repo root — runtime deps for Vercel Python function
- [x] `DEMANDOS_RUNTIME_MODE=local|vercel` — controls filesystem + DB behaviour
- [x] `DEMANDOS_DEMO_SCALE=full|small` — controls demo seed size (small=10 products, 2 stores, 180 days)
- [x] Training service: uses `/tmp` for artifacts in vercel mode; records `vercel_ephemeral` in DB
- [x] Health/readiness: `/api/readiness` returns `not_ready` when vercel mode + no Postgres URL
- [x] DB session: logs warning (not crash) when vercel + SQLite; health surface failure clearly
- [x] Frontend API client: same-origin `/api` calls when `NEXT_PUBLIC_API_BASE_URL` is blank
- [x] `apps/web/.env.example` — documents same-origin mode for single Vercel project
- [x] `docs/deployment.md` — full single Vercel project setup guide with Neon Postgres
- [x] `docs/operator_runbook.md` — Vercel operator instructions added
- [x] `docs/demo_runbook.md` — Vercel demo instructions added
- [x] `test_vercel_deployment.py` — tests J1-J8 (vercel.json, adapter import, readiness, scale, key guard)
- [x] `scripts/verify.sh` updated with Sprint 10B checks
- [x] All existing tests still pass

**Required Vercel env vars for single-project mode:**
```
DATABASE_URL          ← injected by Neon Marketplace integration
DEMANDOS_API_KEY      ← set in Vercel env vars panel
DEMANDOS_RUNTIME_MODE = vercel
DEMANDOS_DEMO_SCALE   = small
```
`NEXT_PUBLIC_API_BASE_URL` must be **left blank** for same-origin API calls.

## Sprint 11 — Production Smoke Validation, Observability Polish, Case Study Prep ✅
- [x] `scripts/smoke_production.py` — 15-check production smoke script (read-only by default)
- [x] `GET /api/observability/runs-summary` — per-stage run status, runtime mode, demo scale
- [x] `GET /api/observability/failure-summary` — latest failure per stage, bounded to 20
- [x] `GET /api/readiness` polished — adds `database`, `api_key_guard_enabled`,
      `external_side_effects_enabled`, `checks` (named safety checks, no secrets)
- [x] `GET /api/runtime/check` — new endpoint: runtime config without secrets
- [x] Sidebar label updated from "Sprint 9 · Dashboard UX" to "Deployed MVP · Demo Mode"
- [x] Runtime status indicator in sidebar (fetches `/api/readiness` — runtime/scale/data)
- [x] `ErrorState` improved — distinguishes API key errors, backend unavailable, no data
- [x] `EmptyState` improved — `showPipelineLink` prop guides user to Pipeline Controls
- [x] `docs/case_study.md` — full portfolio case study draft
- [x] `docs/demo_script.md` — 3–5 minute presenter walkthrough script
- [x] `docs/case_study_assets.md` — 12-screenshot checklist with filenames and proof points
- [x] `docs/screenshots/README.md` — updated with Sprint 11 screenshot list
- [x] `docs/final_qa_checklist.md` — deployment, pipeline, dashboard, security, docs checklist
- [x] `apps/api/tests/test_sprint11.py` — 28 tests covering all Sprint 11 requirements
- [x] `scripts/verify.sh` updated with Sprint 11 checks
- [x] All existing tests still pass

**Sprint 11 counts (Vercel small mode):**
- Products: 10
- Stores: 2
- Orders: ~1,677
- Inventory snapshots: ~1,156
- Feature rows: ~1,154
- Baseline forecast rows: ~946
- Planning forecast rows: ~560
- Stockout risk rows: 20
- Reorder recommendations: 10

**No new ML formulas, no real purchase orders, no external side effects.**

## Sprint 12 — Final Portfolio Case Study, Screenshots, and MVP Closeout
- [ ] Capture all 12 portfolio screenshots
- [ ] Finalize `docs/case_study.md` with real screenshot references
- [ ] Polish public README with architecture diagram
- [ ] Add architecture diagram (Mermaid or SVG)
- [ ] Run final deployed smoke test with pipeline
- [ ] Mark MVP complete
