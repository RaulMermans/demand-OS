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
| Ops | ingestion_runs, aggregation_runs, pipeline_events | IngestionService, AggregationService | 1–2 |
| Clean | orders_clean, inventory_clean, promotions_clean, products_clean, stores_clean, suppliers_clean, purchase_orders_clean | AggregationService | 2 |
| Aggregate | sales_daily, inventory_daily, promotion_daily, product_store_daily | AggregationService | 2 |
| Feature | feature_matrix | FeatureService | 3 |
| Model | forecast_runs, forecasts, model_metrics | ForecastingService | 4 |
| ML Model | model_versions | TrainingService | 5 |
| Risk | stockout_risk_runs, stockout_risks | StockoutService | 6 |
| Recommendation | reorder_recommendations | RecommendationService | 7 (planned) |

## Key Design Decisions

- **Deterministic pipeline**: each layer reads from DB, writes to DB. No stateful in-memory chains.
- **Connector abstraction**: swap data sources without touching pipeline code.
- **Raw-data-only input**: connectors never compute ML features, forecasts, or risk scores.
- **Global ML model**: one LightGBM model trained across all SKU/store series (Nixtla/mlforecast pattern).
- **28-day forecast horizon**: aligned with M5 competition framing.
- **No automatic purchases**: recommendations are suggestions only; human approval required.

See `docs/decisions/` for formal architecture decision records.
