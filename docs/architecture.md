# DemandOS — Architecture

## System Overview

DemandOS is a deterministic ML pipeline for demand forecasting and inventory risk management.
It ingests raw operational commerce records and computes all derived insights internally.

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  MockConnector │ CsvConnector │ ShopifyConnector │ ERPConnector │
└───────────────────────┬─────────────────────────────────────────┘
                        │ raw operational records
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                               │
│  IngestionService → ValidationService → raw_* tables (DB)       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGGREGATION LAYER                              │
│  AggregationService → *_clean + sales_daily + inventory_daily   │
│                     + promotion_daily + product_store_daily (DB) │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FEATURE LAYER                                  │
│  FeatureService → feature_matrix (DB)                           │
│  (lag features, rolling windows, calendar, promotions,          │
│   inventory state, supplier lead times)                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MODEL LAYER                                    │
│  ForecastingService → ModelVersion, ForecastRun, Forecast (DB)  │
│  LightGBM global model · naive baseline · prediction intervals  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   RISK LAYER  (Sprint 6)                        │
│  StockoutService → stockout_risk_runs + stockout_risks (DB)     │
│  Inputs: forecasts + inventory_daily + POs + supplier info      │
│  Outputs: risk_tier, risk_score, days_until_stockout,           │
│           safety_stock, coverage_ratio, lost_sales_estimate     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                RECOMMENDATION LAYER  (Sprint 7)                  │
│  RecommendationService → recommendation_runs +                   │
│                          reorder_recommendations (DB)            │
│  Inputs: stockout_risks + raw_products                           │
│  Computes: lead_time_demand, reorder_point, inventory_position,  │
│            recommended_units, urgency, reason, confidence        │
│  Recommendation-only: no purchase orders, no external calls      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API / DASHBOARD  (Sprint 8–10)                │
│  FastAPI (port 8000)             Next.js (port 3000)            │
│  /health /api/overview           / /overview /forecasts         │
│  /api/forecasts /api/risks       /risks /recommendations        │
│  /api/recommendations            /model-performance /data-health│
│  /api/dashboard/overview         /pipeline (controls + run log) │
│  /api/dashboard/pipeline-status  /products/[productId] drilldown│
│  /api/dashboard/product/{id}     Typed API client: lib/api.ts   │
│  /api/demo/run-full-pipeline     Response types: lib/types.ts   │
│  /api/demo/pipeline-runs         Charts: recharts                │
│  /api/demo/pipeline-runs/latest  BarChartPanel, LineChartPanel  │
│  Alembic migrations              KpiCard, PipelineControlButton  │
│  API key guard (Sprint 9):       ApiKeyInput (sessionStorage)    │
│    X-DemandOS-API-Key header     EmptyState, StatusBadge,        │
│    on all write/control POST     DataTable, LoadingState         │
│    Disabled when no key set      DurableRunPanel (Sprint 10)     │
│  DemoPipelineService (Sprint 10) Vercel deployment ready         │
│    8-stage orchestration         apps/web/vercel.json            │
│    DemoPipelineRun table         NEXT_PUBLIC_API_BASE_URL        │
└─────────────────────────────────────────────────────────────────┘
```

## Data Layers

| Layer | Tables | Computed By | Sprint |
|-------|--------|-------------|--------|
| Raw | raw_products, raw_stores, raw_orders, raw_inventory_snapshots, raw_promotions, raw_suppliers, raw_purchase_orders | connectors | 1 |
| Ops | ingestion_runs, aggregation_runs, pipeline_events | IngestionService, AggregationService | 1–2 |
| Clean | orders_clean, inventory_clean, promotions_clean, products_clean, stores_clean, suppliers_clean, purchase_orders_clean | AggregationService | 2 |
| Aggregate | sales_daily, inventory_daily, promotion_daily, product_store_daily | AggregationService | 2 |
| Feature | feature_matrix | FeatureService | 3 |
| Model | forecast_runs, forecasts, model_metrics | ForecastingService | 4 |
| ML Model | model_versions | TrainingService | 5 |
| Risk | stockout_risk_runs, stockout_risks | StockoutService | 6 |
| Recommendation | recommendation_runs, reorder_recommendations | RecommendationService | 7 |
| API Contracts | schemas/api.py Pydantic response types | Sprint 8 | 8 |
| Migrations | Alembic alembic/versions/ | Alembic | 8 |
| Dashboard UX | Charts, pipeline controls, API key guard | Sprint 9 | 9 |
| Demo Orchestration | demo_pipeline_runs | DemoPipelineService | 10 |

## API Contract Standards (Sprint 8)

- All endpoints return explicit Pydantic schemas (no raw ORM objects)
- List endpoints have bounded pagination (`limit`/`offset`); max limits enforced
- No-data states return predictable status strings (`no_data`, `no_forecast`, etc.)
- Dashboard endpoints (`GET /api/dashboard/*`) aggregate computed data only
- `PATCH /api/recommendations/{id}/status` never creates purchase orders
- Frontend uses typed client (`lib/api.ts`) and explicit types (`lib/types.ts`)

## Key Design Decisions

- **Deterministic pipeline**: each layer reads from DB, writes to DB. No stateful in-memory chains.
- **Connector abstraction**: swap data sources without touching pipeline code.
- **Raw-data-only input**: connectors never compute ML features, forecasts, or risk scores.
- **Global ML model**: one LightGBM model trained across all SKU/store series (Nixtla/mlforecast pattern).
- **28-day forecast horizon**: aligned with M5 competition framing.
- **No automatic purchases**: recommendations are suggestions only; human approval required.
- **API key guard** (Sprint 9): write/control endpoints optionally require `X-DemandOS-API-Key` header. When `DEMANDOS_API_KEY` env var is empty (default), the guard is disabled for local development. The key is never logged or stored in the database.
- **Pipeline controls** (Sprint 9): each pipeline stage can be triggered from the `/pipeline` dashboard page. The "Run Full Demo Pipeline" button runs all 8 stages sequentially, stops on failure, and requires confirmation before reset.

See `docs/decisions/` for formal architecture decision records.
