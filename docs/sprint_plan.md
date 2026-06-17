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

## Sprint 4 — Forecasting
- [ ] Train LightGBM global model on feature matrix
- [ ] Generate 28-day forecasts per product/store
- [ ] Compute 90% prediction intervals
- [ ] Forecast Explorer page (charts with Recharts)
- [ ] Walk-forward CV evaluation

## Sprint 5 — Stockout Risk + Reorder
- [ ] Implement StockoutService:
  - Days-until-stockout calculation
  - Safety stock (Z × σ × √LT)
  - Risk tier assignment (critical / high / medium / low)
- [ ] Implement RecommendationService:
  - Reorder point (ROP)
  - Economic Order Quantity (EOQ)
  - Supplier + delivery date
- [ ] Inventory Risk heatmap page
- [ ] Recommendations table

## Sprint 6 — Model Evaluation + Observability
- [ ] Implement EvaluationService (RMSE, MAE, SMAPE, WRMSSE, bias, coverage)
- [ ] Model Performance dashboard
- [ ] Pipeline event logging
- [ ] Alerting stubs (critical stockout → notification)

## Sprint 7+ — Connectors + Production
- [ ] CsvCommerceConnector (real file parsing)
- [ ] ShopifyConnector (Admin API)
- [ ] WooCommerceConnector
- [ ] Alembic migrations
- [ ] Auth (API keys or JWT)
- [ ] Deployment: Vercel + Railway/Fly
