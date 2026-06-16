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

## Sprint 2 — Aggregation Pipeline
- [ ] Implement AggregationService:
  - Daily sales aggregation per product/store
  - Inventory daily snapshot aggregation
  - Days-of-supply calculation
  - Promotion flag join
- [ ] Populate sales_daily and inventory_daily tables
- [ ] Run aggregation automatically after ingestion
- [ ] Overview page with live DB counts

## Sprint 3 — Feature Engineering
- [ ] Implement FeatureService:
  - Lag features (7d, 14d, 28d)
  - Rolling window stats (mean, std)
  - Calendar features
  - Promotion features
  - Inventory features
- [ ] Populate feature_matrix table
- [ ] Add feature inspector to data health page

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
