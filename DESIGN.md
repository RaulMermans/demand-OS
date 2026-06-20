# DemandOS — Design Document

## System Architecture

DemandOS is a deterministic ML pipeline split into six layers:

```
Raw → Clean → Aggregate → Feature → Model → Decision
```

### Layer Details

| Layer | Tables | Service | Sprint |
|-------|--------|---------|--------|
| Raw | raw_products, raw_stores, raw_orders, raw_inventory_snapshots, raw_promotions, raw_suppliers, raw_purchase_orders | IngestionService + ValidationService | 1 |
| Ops | ingestion_runs, aggregation_runs, pipeline_events | IngestionService, AggregationService | 1–2 |
| Clean | orders_clean, inventory_clean, promotions_clean, products_clean, stores_clean, suppliers_clean, purchase_orders_clean | AggregationService | 2 |
| Aggregate | sales_daily, inventory_daily, promotion_daily, product_store_daily | AggregationService | 2 |
| Feature | feature_matrix | FeatureService | 3 |
| Model | model_versions, forecast_runs, forecasts | ForecastingService | 4 |
| Risk | stockout_risk_runs, stockout_risks | StockoutService | 6 |
| Recommendation | recommendation_runs, reorder_recommendations | RecommendationService | 7 |
| Evaluation | model_metrics | EvaluationService | 5–6 |

---

## Core Workflow

```
1.  Connector.fetch_*()                       → raw Pydantic objects
2.  IngestionService.run()                    → writes to raw_* tables
3.  ValidationService.validate()              → emits PipelineEvents for errors
4.  AggregationService.run()                  → writes to *_clean, sales_daily, inventory_daily
5.  FeatureService.build_feature_matrix()     → writes to feature_matrix
6.  ForecastingService.run_baseline_forecast()→ writes to forecast_runs, forecasts
7.  ForecastingService.run_planning_forecast()→ writes forward-planning forecast rows
8.  StockoutService.run_stockout_risk()       → writes to stockout_risk_runs, stockout_risks
9.  RecommendationService.run_reorder_recommendations() → writes to recommendation_runs,
                                                          reorder_recommendations
10. EvaluationService.evaluate()              → writes to model_metrics
11. FastAPI serves all outputs                → Next.js dashboard reads from API
```

---

## Connector Design

All connectors implement `BaseCommerceConnector` (abstract base class).
The protocol is defined in `app/connectors/base.py`.

```python
class BaseCommerceConnector:
    def fetch_products(self) -> list[RawProduct]: ...
    def fetch_stores(self) -> list[RawStore]: ...
    def fetch_orders(self, start_date, end_date) -> list[RawOrderLine]: ...
    def fetch_inventory_snapshots(self, start_date, end_date) -> list[RawInventorySnapshot]: ...
    def fetch_promotions(self, start_date, end_date) -> list[RawPromotion]: ...
    def fetch_suppliers(self) -> list[RawSupplier]: ...
    def fetch_purchase_orders(self, start_date, end_date) -> list[RawPurchaseOrder]: ...
```

Swapping connectors requires zero changes to pipeline services — only the
connector instance passed to `IngestionService` changes.

---

## Dashboard Pages

| Route | Data Source | Sprint |
|-------|-------------|--------|
| `/` | /api/status | 0 (scaffold) |
| `/overview` | /api/overview + /api/dashboard/pipeline-status | 2, 9 |
| `/forecasts` | /api/dashboard/forecast-summary + product drilldown | 4, 9 |
| `/risks` | /api/dashboard/risk-summary + /api/risks | 6, 9 |
| `/model-performance` | /api/metrics + /api/dashboard/model-summary | 5–6 |
| `/data-health` | /api/data-health | 1 |
| `/recommendations` | /api/recommendations + urgency chart | 7–9 |
| `/pipeline` | /api/dashboard/pipeline-status (write: all pipeline POSTs) | 9 |

## API Key Guard (Sprint 9)

When `DEMANDOS_API_KEY` is set in the environment, all POST/PATCH write and control
endpoints require the header `X-DemandOS-API-Key: <key>`. Read-only GET endpoints
remain public for demo visibility.

Protected endpoints: `POST /api/demo/reset`, `POST /api/ingestion/run`,
`POST /api/aggregation/run`, `POST /api/features/build`,
`POST /api/forecasts/baseline/run`, `POST /api/forecasts/planning/run`,
`POST /api/models/train`, `POST /api/risks/run`, `POST /api/recommendations/run`,
`PATCH /api/recommendations/{id}/status`

When `DEMANDOS_API_KEY` is not set (default), the guard is disabled and all requests
pass — designed for local development.

The API key is:
- Never logged or stored in the database
- Never hardcoded in frontend code
- Stored in sessionStorage (not localStorage) when entered via the `/pipeline` UI
- Cleared when the browser tab closes

---

## Key Tradeoffs

### Global ML model vs. per-SKU models
**Decision:** Global model (one LightGBM across all series).
**Why:** Low-volume SKUs have insufficient history for per-SKU models.
Global model transfers learning across similar products.
**Tradeoff:** Less customization per SKU; compensated by rich feature engineering.

### SQLite (dev) vs. Postgres (prod)
**Decision:** SQLite for development/testing, Postgres for production.
**Why:** SQLite has zero setup friction; Postgres handles concurrent writes and
large datasets required in production.
**Tradeoff:** Minor dialect differences (use SQLAlchemy to abstract them).

### Deterministic pipeline vs. agentic system
**Decision:** Deterministic pipeline (see ADR 0001).
**Why:** Reproducibility, testability, auditability, safety.
**Tradeoff:** Less adaptive to novel data shapes; requires code changes to evolve.

### 28-day forecast horizon
**Decision:** 28 days (4 weeks).
**Why:** Aligned with M5 competition standard; covers typical supplier lead times (7–21 days).
**Tradeoff:** Longer horizons are less accurate; shorter horizons miss lead-time risk.

---

## Service Boundaries

Each service has exactly one responsibility:

| Service | Reads | Writes |
|---------|-------|--------|
| IngestionService | connector | raw_* tables, ingestion_runs |
| ValidationService | raw_* tables | pipeline_events |
| AggregationService | raw_* tables | *_clean tables, sales_daily, inventory_daily, promotion_daily, product_store_daily, aggregation_runs |
| FeatureService | sales_daily, inventory_daily, raw_promotions, raw_suppliers | feature_matrix |
| ForecastingService | feature_matrix | model_versions, forecast_runs, forecasts |
| StockoutService | forecasts, inventory_daily, raw_products, raw_suppliers | stockout_risk_runs, stockout_risks |
| RecommendationService | stockout_risks, raw_products | recommendation_runs, reorder_recommendations |
| EvaluationService | forecasts, sales_daily | model_metrics |

Services never call each other. They read from and write to the DB only.
