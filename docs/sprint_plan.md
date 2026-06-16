# DemandOS — Sprint Plan

## Sprint 0 — Scaffold ✅ (Current)
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

## Sprint 1 — Raw Synthetic Commerce Data Generator
- [ ] Implement MockCommerceConnector with realistic synthetic data:
  - 50 products across 5 categories
  - 5 stores across 3 regions
  - 2 years of daily order history (730 days)
  - Weekday / seasonal patterns (Christmas, summer, etc.)
  - 8 promotional events per year
  - Weekly inventory snapshots
  - 10 suppliers with realistic lead times
  - Purchase order history matching demand
- [ ] Implement IngestionService to persist mock records to DB
- [ ] Implement ValidationService with field checks
- [ ] Add /api/data-health live checks
- [ ] Add data health frontend page

## Sprint 2 — Aggregation Pipeline
- [ ] Implement AggregationService:
  - Daily sales aggregation per product/store
  - Inventory daily snapshot aggregation
  - Days-of-supply calculation
  - Promotion flag join
- [ ] Populate sales_daily and inventory_daily tables
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
