# DemandOS — Case Study

## Title

**DemandOS: A Deterministic Demand Forecasting and Inventory Risk Platform**

---

## Summary

DemandOS is a portfolio MVP demonstrating a deterministic machine learning pipeline
for demand forecasting and inventory risk management in retail. Built in 14 sprints
over a single-developer project, it ingests raw synthetic commerce records, runs a
full feature engineering and backtesting pipeline, trains a gradient boosting
forecasting model, scores each product/store pair for stockout risk, and generates
deterministic reorder recommendations — all without any hardcoded metrics or
precomputed outputs. The prototype is deployed on Vercel with a Neon Postgres
backend and serves an interactive Next.js dashboard.

**Live demo:** [https://demand-os-three.vercel.app](https://demand-os-three.vercel.app)

**Validated pipeline output (small mode, seed=42):**
- 10 products × 2 stores × 180 days
- 1,677 orders ingested
- 1,156 inventory snapshots
- 1,154 feature rows (36 leakage-safe columns)
- 946 baseline forecast rows (backtesting window)
- 560 planning forecast rows (28-day forward window)
- 20 stockout risk scores
- 10 reorder recommendations

---

## Problem Statement

Retail operations teams frequently lack tooling that connects raw commerce data
to actionable inventory decisions:

- **When will a product run out?** Inventory snapshots and purchase order histories
  exist in ERPs, but the math to project days-until-stockout is rarely automated.
- **How much should we reorder, and how urgently?** Safety stock and EOQ formulas
  are well-understood but rarely implemented in an end-to-end auditable way.
- **Which forecasting approach actually works on this data?** Off-the-shelf BI tools
  require precomputed or manually maintained datasets and do not expose model
  comparison metrics.

Traditional spreadsheet-based approaches are manual, error-prone, and do not scale
beyond a single analyst. The goal was to build a working pipeline that could serve
as a reference implementation for this class of system.

---

## Constraints

| Constraint | Detail |
|------------|--------|
| No real customer data | Synthetic mock data only (seed=42, reproducible) |
| No real purchase orders | Recommendations are internal suggestions — no external actions |
| No real supplier communication | No emails, webhooks, or ERP write calls |
| Serverless budget | Demo pipeline must complete within Vercel's 60s function timeout in small mode |
| Single developer, 14 sprints | Capabilities layered sequentially, followed by public-release polish |
| No precomputed metrics | Every number the dashboard shows must be computed by the pipeline |

---

## Why Synthetic Raw Data

DemandOS uses synthetic commerce records rather than fake dashboard outputs. This is
a deliberate design choice:

- **Raw data, not fake metrics.** The connector generates realistic orders, inventory
  snapshots, promotions, and purchase orders — the same record types that exist in a
  real ERP or e-commerce platform. All derived values (MAE, risk tiers, safety stock,
  reorder quantities) are calculated from those records, not invented.
- **Proves the pipeline end-to-end.** Because the raw data is generated from realistic
  distributions, the pipeline must actually work to produce sensible outputs. If the
  risk engine produced impossible results, the test suite would catch it.
- **Reproducible.** Using `seed=42` ensures identical results every time, making demo
  sessions consistent and letting reviewers verify outputs.

---

## Architecture Decision

**DemandOS is deterministic, not agentic.**

An LLM-based agentic pipeline would make the system non-reproducible, untestable,
and unauditable — the opposite of what an inventory risk system needs. Instead, every
computation is a deterministic function from inputs to outputs, each stage writing to
the database before the next stage reads from it.

See [docs/decisions/0001-deterministic-ml-workflow.md](decisions/0001-deterministic-ml-workflow.md).

---

## System Architecture

```
Connector (MockCommerceConnector)
    │  raw operational records
    ▼
IngestionService + ValidationService
    │  raw_* tables (Postgres)
    ▼
AggregationService
    │  *_clean, sales_daily, inventory_daily,
    │  promotion_daily, product_store_daily
    ▼
FeatureService
    │  feature_matrix (36 leakage-safe columns)
    ▼
ForecastingService (baselines) + TrainingService (HistGradientBoosting)
    │  forecast_runs, forecasts, model_metrics, model_versions
    ▼
StockoutService
    │  stockout_risk_runs, stockout_risks
    ▼
RecommendationService
    │  recommendation_runs, reorder_recommendations
    ▼
FastAPI → Next.js Dashboard
```

**Deployment:**
```
Browser → Vercel Next.js UI → Vercel FastAPI Function → Neon Postgres
```

Everything is stateless per request. No background jobs. No message queues.
No in-memory chains between services.

---

## Data Model and Raw-Data-Only Principle

The raw-data-only principle is enforced at three levels:

1. **Schema-level:** `apps/api/app/schemas/raw.py` contains only operational record
   types. A pytest test (`test_raw_data_rule.py`) runs on every CI push and fails if
   any derived field (lag features, forecasts, risk scores, safety stock) appears in
   a raw schema class.
2. **Connector-level:** Connectors return only raw schemas. `test_connector_contract.py`
   enforces this.
3. **Pipeline-level:** Each service reads its inputs from the database and writes its
   outputs to the database. There is no mechanism for a service to pass derived data
   back upstream to a connector.

| Layer | Schema file | Example columns |
|-------|-------------|-----------------|
| Raw | `schemas/raw.py` | `quantity_ordered`, `on_hand_units`, `unit_cost` |
| Derived | `schemas/derived.py` | `risk_tier`, `recommended_units`, `wape` |
| ORM | `db/models.py` | All tables — `feature_matrix`, `forecasts`, `stockout_risks` |

---

## Pipeline Walkthrough

| Stage | Service | Inputs | Outputs |
|-------|---------|--------|---------|
| Ingestion | IngestionService + ValidationService | Connector records | `raw_*` tables |
| Aggregation | AggregationService | `raw_*` tables | `sales_daily`, `inventory_daily`, `product_store_daily` |
| Feature engineering | FeatureService | `product_store_daily` | `feature_matrix` (36 columns) |
| Baseline forecasting | ForecastingService | `feature_matrix` | `forecasts` (backtesting window) |
| ML training | TrainingService | `feature_matrix` | `model_versions`, `model_metrics`, `forecasts` |
| Planning forecast | ForecastingService | `feature_matrix` | `forecasts` (28-day forward window) |
| Stockout risk | StockoutService | `forecasts`, `inventory_daily`, POs | `stockout_risks` |
| Recommendations | RecommendationService | `stockout_risks`, `raw_products` | `reorder_recommendations` |

The full pipeline runs in approximately 25–40 seconds in small mode (10 products,
2 stores, 180 days) within a single Vercel serverless function invocation.

---

## Forecasting and Model Evaluation

**Baseline models (rule-based):**
- Seasonal naive: `forecast(D) = units_sold(D-7)` — last same weekday
- Moving average 7d: `rolling_units_mean_7d` (shifted to avoid leakage)
- Moving average 28d: `rolling_units_mean_28d`

**ML model:**
- Algorithm: `HistGradientBoostingRegressor` (scikit-learn) — handles missing values natively
- Training: global model across all (product, store) series
- Features: 30 leakage-safe features — lag, rolling, calendar, promo, price/margin, inventory, lifecycle
- Encoding: `OrdinalEncoder` with sorted categories for deterministic encoding
- Evaluation: train/test split by date; test window = last `backtest_days` of feature matrix
- Predictions clipped at 0; ±1σ heuristic p10/p90 intervals

**Leakage prevention:**
- All lag and rolling features use `shift(1)` before rolling — window ends at D-1
- Pre-launch rows (`days_since_launch < 0`) excluded from training
- `target_units_sold` is the supervised label; it is never a feature

**Honest reporting:**
- The ML model is compared against baselines without forcing it to win
- WAPE, MAE, RMSE, SMAPE, and Bias reported per overall / category / store
- Metrics with zero denominators return `null` rather than infinity

---

## Inventory Risk Scoring (Stockout Risk)

**Inputs:**
- Current inventory from `inventory_daily` (latest snapshot on/before `as_of_date`)
- Inbound POs (status: submitted/confirmed) within the horizon window
- Supplier lead time from `raw_suppliers.lead_time_days_max`
- Forecast demand: `sum(p50_units)` and `sum(p90_units)` over horizon

**Computed fields:**
- `projected_end_inventory_p50 = current_available + inbound - demand_p50`
- `projected_end_inventory_p90 = current_available + inbound - demand_p90`
- `days_until_stockout` (null when no projected stockout within horizon)
- `safety_stock = 1.65 × rolling_std_7d × √lead_time`
- `inventory_coverage_ratio = current_available / (average_daily_forecast × lead_time)`
- `lost_sales_units_estimate`, `lost_sales_value_estimate`

**Risk tier (deterministic rules):**

| Tier | Condition |
|------|-----------|
| `critical` | `days_until_stockout ≤ lead_time` OR `projected_p50 ≤ 0` |
| `high` | `projected_p50 ≤ safety_stock` OR `coverage_ratio < 1.0` |
| `medium` | `projected_p90 ≤ safety_stock` OR `coverage_ratio < 1.5` |
| `low` | Well-covered inventory |
| `unknown` | Insufficient data |

---

## Reorder Recommendations and Safety Boundary

**Formulas:**
- `inventory_position = current_available + inbound_within_horizon`
- `lead_time_demand = average_daily_forecast × supplier_lead_time_days`
- `reorder_point = lead_time_demand + safety_stock`
- `recommended_units = max(0, reorder_point - inventory_position)`
- `estimated_order_cost = recommended_units_rounded × unit_cost`

**Urgency rules:**
- `critical`: risk_tier=critical OR days_until_stockout ≤ 7
- `high`: risk_tier=high OR days_until_stockout ≤ supplier_lead_time_days
- `medium`: risk_tier=medium OR recommended_units > 0
- `low`: otherwise

**Safety boundary — what DemandOS does NOT do:**
- Does not create real purchase orders
- Does not transmit orders to suppliers
- Does not send emails or Slack notifications
- Does not trigger any automatic purchasing action

Approved recommendations remain at `approved_internal` status — approved inside
DemandOS only. No external action is taken.

---

## Dashboard Walkthrough

| Page | URL | What it shows |
|------|-----|---------------|
| Home | `/` | KPI cards: products, orders, snapshots, pipeline status, risk/rec summary |
| Overview | `/overview` | Aggregated KPIs with honest pipeline readiness indicators |
| Forecasts | `/forecasts` | Product selector + p10/p50/p90 line chart from stored forecasts |
| Inventory Risk | `/risks` | Risk queue ranked by tier; days-until-stockout, coverage ratio |
| Recommendations | `/recommendations` | Reorder queue with urgency, units, cost, approval status |
| Model Performance | `/model-performance` | ML vs baseline WAPE/MAE/RMSE — honest comparison |
| Data Health | `/data-health` | Raw + canonical table counts, check list, run history |
| Pipeline Controls | `/pipeline` | Step-by-step controls; full pipeline run with durable log |
| Product Drilldown | `/products/{id}` | Per-product forecast chart + risk per store + recommendations |
| CSV Upload | `/csv-upload` | Raw-data template guidance, validation summary, errors, and upload history |
| Monitoring | `/monitoring` | Previous-vs-latest model and data-health comparisons |
| Scenarios | `/scenarios` | Simulated, non-mutating before/after risk comparisons |
| Connectors | `/connectors` | Disabled connector status, config validation, and no-network dry runs |

All values on all pages are fetched live from the API. No hardcoded metrics.

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Vercel Project (deployed from repo root ./)             │
│                                                          │
│  / → apps/web (Next.js — @vercel/next)                  │
│  /api/* → api/index.py (FastAPI — @vercel/python)       │
│                                                          │
│  Environment variables:                                  │
│    DATABASE_URL          ← Neon Postgres (Marketplace)   │
│    DEMANDOS_API_KEY      ← write-endpoint guard          │
│    DEMANDOS_RUNTIME_MODE = vercel                        │
│    DEMANDOS_DEMO_SCALE   = small                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Neon Postgres (Vercel Marketplace integration)          │
│  DATABASE_URL injected automatically                     │
└─────────────────────────────────────────────────────────┘
```

**Serverless limitations acknowledged:**
- Model artifacts written to `/tmp` are ephemeral; `ModelVersion.artifact_path = "vercel_ephemeral"`
  documents this — retraining is required after cold start if a serialized model is needed
- No background jobs; pipeline runs synchronously within a single serverless request
- Cold starts may be slow (3–8 seconds) after inactivity
- 60-second function timeout limits data scale; production use would require a dedicated backend

---

## Reliability, Testing, and Observability

**Backend verification:** the complete pytest suite passes using isolated test
databases, with no external API dependency required for CI.

| Test file | Coverage |
|-----------|----------|
| `test_raw_data_rule.py` | Connector raw-data-only contract |
| `test_connector_contract.py` | Connector output schemas |
| `test_api_key_guard.py` | Write endpoint protection (401 when key set) |
| `test_vercel_deployment.py` | Single-project adapter wiring |
| `test_api_contracts.py` | All API response shapes |
| `test_aggregation.py` | Aggregation idempotency and reconciliation |
| `test_features.py` | Feature engineering leakage prevention |
| `test_forecasting.py` | Forecast runs and model metrics |
| `test_stockout.py` | Risk tier logic and edge cases |
| `test_recommendations.py` | Recommendation formulas and status workflow |
| `test_sprint11.py` | Observability, readiness, smoke script |

**`scripts/verify.sh`:** 100+ structural checks — required files, schema purity, migration
count, Vercel adapter, Sprint 10/11 additions, no secrets committed.

**`scripts/smoke_production.py`:** 18-check deployed endpoint validation — readiness,
all dashboard endpoints, runtime mode, demo scale, core data counts, no secret leak.

**Observability endpoints:**
- `GET /api/observability/runs-summary` — aggregated run counts per pipeline stage
- `GET /api/observability/failure-summary` — recent failures per stage
- `GET /api/runtime/check` — Vercel runtime info (no secrets)
- `GET /api/readiness` — database connection, runtime mode, demo scale, API key guard

**CI (GitHub Actions):**
- `backend`: Python 3.11, pytest, verify.sh
- `frontend`: Node LTS, npm build
- `repo-hygiene`: no `.env`, no artifacts, no secrets

---

## Screenshots

Core screenshots 1–9 were captured via Playwright against the deployed app before
the Sprint 14 visual refresh. They are scheduled for recapture after the refreshed
deployment. Advanced screenshots 13–16 are also pending that deployment; Vercel,
Neon, and GitHub Actions views remain manual and require redaction.

| File | Page | What it proves |
|------|------|----------------|
| [`01-readiness.png`](screenshots/01-readiness.png) | `/api/readiness` | Vercel live, Neon connected, no secrets exposed |
| [`02-home-dashboard.png`](screenshots/02-home-dashboard.png) | `/` | Live KPI cards from pipeline |
| [`03-pipeline-completed.png`](screenshots/03-pipeline-completed.png) | `/pipeline` | All 8 steps completed with timestamps |
| [`04-forecasts.png`](screenshots/04-forecasts.png) | `/forecasts` | p10/p50/p90 forecast line chart |
| [`05-inventory-risk.png`](screenshots/05-inventory-risk.png) | `/risks` | Risk tier queue with days-until-stockout |
| [`06-recommendations.png`](screenshots/06-recommendations.png) | `/recommendations` | Reorder queue with urgency and cost estimates |
| [`07-model-performance.png`](screenshots/07-model-performance.png) | `/model-performance` | Honest ML vs baseline comparison |
| [`08-data-health.png`](screenshots/08-data-health.png) | `/data-health` | Table counts and health checks |
| [`09-product-drilldown.png`](screenshots/09-product-drilldown.png) | `/products/prod_008` | Per-product forecast + risk + recs |
| `10-vercel-deployment.png` | Vercel dashboard | Single-project deployment (**pending manual capture**) |
| `11-neon-connection-redacted.png` | Vercel Storage | Neon integration panel (**pending manual capture**) |
| `12-ci-passing.png` | GitHub Actions | All CI jobs green (**pending manual capture**) |
| `13-csv-upload.png` | `/csv-upload` | Raw-data validation/upload workflow (**pending refreshed deploy**) |
| `14-monitoring.png` | `/monitoring` | Model/data comparison dashboard (**pending refreshed deploy**) |
| `15-scenarios.png` | `/scenarios` | Simulated before/after comparison (**pending refreshed deploy**) |
| `16-connectors.png` | `/connectors` | Disabled connector readiness (**pending refreshed deploy**) |

---

## Results

The deployed prototype at `https://demand-os-three.vercel.app` demonstrates:

1. A full raw → feature → forecast → risk → recommendation pipeline running end-to-end
   on synthetic retail data, producing sensible and auditable outputs.
2. A Next.js dashboard where every metric is fetched live from the API — no hardcoded
   business figures anywhere in the frontend.
3. Serverless deployability on a free Vercel + Neon tier with ~35-second full pipeline
   runs in small mode.
4. A comprehensive backend suite covering every pipeline stage; `verify.sh` with structural
   checks; and a production smoke script that validates 18 conditions against the
   live deployment.

**Validated smoke test results (2026-06-21):** 18/18 checks passed.

---

## What Is Intentionally Not Implemented

| Feature | Reason |
|---------|--------|
| Real Shopify/WooCommerce/ERP connectors | Requires API credentials; out of scope for portfolio MVP |
| Real purchase order creation | Safety boundary — recommendations are internal only |
| Email/Slack notifications | External side effects; excluded by design |
| User accounts / JWT auth | Overkill for single-operator demo |
| Automated monitoring alerts | Monitoring is visible in-app; no email/Slack side effects |
| Calibrated probabilistic intervals | p10/p90 are ±1σ heuristics, documented as such |
| Background schedulers (cron) | Serverless constraint; out of scope |
| Multi-tenant support | Single-operator demo |
| Large-file ingestion | CSV upload is intentionally limited to 2 MB |

---

## Future Roadmap

**Future work:**
- Live connectors only after credential, privacy, retry, and rate-limit design
- Calibrated prediction intervals (conformal prediction)
- Scheduled monitoring and alert delivery behind explicit operator controls

**Infrastructure (if moving beyond prototype):**
- Dedicated FastAPI backend on Render/Railway/Fly.io (removes Vercel 60s limit)
- Scheduled pipeline runs (Celery + Redis, or Temporal)
- User accounts with scoped API keys
- Prometheus + Grafana for pipeline run metrics

---

## Sprint 13 — Optional Feature Consolidation

Sprint 13 added four bounded, portfolio-oriented capabilities:

- **CSV upload mode** validates raw operational records before ingestion, enforces
  a 2 MB limit, and rejects derived fields.
- **Monitoring dashboard** compares the latest model and data-health signals with
  the previous completed run using documented thresholds.
- **Scenario planning** stores simulated what-if results separately and never
  mutates canonical forecasts, risks, recommendations, or inventory.
- **Connector preparation** keeps Shopify and WooCommerce as disabled connector
  stubs. Configuration validation and dry runs make no live API calls.

## Sprint 14 — Public Release Polish

Sprint 14 focused on presentation and trust rather than new product behavior:

- Refreshed the dashboard with a calm off-white, indigo, slate, emerald, amber,
  and rose visual system.
- Standardized navigation, page headers, KPI cards, tables, badges, forms, charts,
  loading states, empty states, and error states.
- Added a public-readiness audit for secrets, database URLs, generated data,
  model artifacts, duplicate files, and forbidden environment files.
- Updated the README, portfolio draft, screenshot plan, QA checklist, and release notes.

## Final Status

**DemandOS is a portfolio prototype. MVP is complete.**

- All pipeline stages implemented and working end-to-end.
- Deployed and reachable at `https://demand-os-three.vercel.app`.
- All dashboard pages show real computed data — no hardcoded metrics.
- Backend tests, frontend build, structural verification, and public-readiness scan pass.
- Production smoke script passes: 18/18 checks against the live deployment.
- 9 core application screenshots exist from Sprint 12; refreshed captures and four
  advanced-page screenshots are pending the Sprint 14 deployment. Three infrastructure
  screenshots require manual authenticated capture and redaction.

This is not a production inventory management system or a customer deployment. It
is an honest, internal-tool-style portfolio MVP demonstrating what a demand
forecasting pipeline looks like under the hood —
from raw data ingestion to actionable reorder recommendations.
