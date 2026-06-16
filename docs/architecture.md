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
│  AggregationService → sales_daily, inventory_daily (DB)         │
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
│                   DECISION LAYER                                 │
│  StockoutService    → stockout_risks (DB)                       │
│  RecommendationSvc  → reorder_recommendations (DB)              │
│  EvaluationService  → model_metrics (DB)                        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API / DASHBOARD                               │
│  FastAPI (port 8000)      Next.js dashboard (port 3000)         │
│  /health /api/overview    / /overview /forecasts /risks         │
│  /api/forecasts           /model-performance /data-health        │
│  /api/risks                                                     │
│  /api/recommendations                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Data Layers

| Layer | Tables | Computed By | Sprint |
|-------|--------|-------------|--------|
| Raw | raw_products, raw_stores, raw_orders, raw_inventory_snapshots, raw_promotions, raw_suppliers, raw_purchase_orders | connectors | 1 |
| Ops | ingestion_runs, pipeline_events | IngestionService | 1 |
| Aggregate | sales_daily, inventory_daily | AggregationService | 2 |
| Feature | feature_matrix | FeatureService | 3 |
| Model | model_versions, forecast_runs, forecasts | ForecastingService | 4 |
| Decision | stockout_risks, reorder_recommendations, model_metrics | StockoutService, RecommendationService, EvaluationService | 5–6 |

## Key Design Decisions

- **Deterministic pipeline**: each layer reads from DB, writes to DB. No stateful in-memory chains.
- **Connector abstraction**: swap data sources without touching pipeline code.
- **Raw-data-only input**: connectors never compute ML features, forecasts, or risk scores.
- **Global ML model**: one LightGBM model trained across all SKU/store series (Nixtla/mlforecast pattern).
- **28-day forecast horizon**: aligned with M5 competition framing.
- **No automatic purchases**: recommendations are suggestions only; human approval required.

See `docs/decisions/` for formal architecture decision records.
