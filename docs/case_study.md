# DemandOS — Case Study

## Title

**DemandOS: A Synthetic-Data Demand Forecasting and Inventory Risk Platform**

---

## One-Paragraph Summary

DemandOS is a portfolio MVP demonstrating a deterministic machine learning pipeline
for demand forecasting and inventory risk management in retail. Built in 11 sprints,
it ingests raw synthetic commerce records, runs a full feature engineering pipeline,
trains a gradient boosting forecasting model, scores each product/store pair for
stockout risk, and generates deterministic reorder recommendations — all without
any hardcoded metrics or precomputed outputs. The prototype is deployed on Vercel
with a Neon Postgres backend and serves an interactive Next.js dashboard.

---

## Problem Statement

Retail operations teams frequently lack tooling that connects raw commerce data
(orders, inventory snapshots, purchase orders) to actionable insights:
- **When will a product stock out?**
- **How much should we reorder, and how urgently?**
- **Which forecasting model actually performs better on our data?**

Traditional spreadsheet-based approaches are manual, error-prone, and do not scale.
Off-the-shelf BI tools require precomputed or manually maintained datasets, which
defeats the purpose of an automated pipeline.

---

## Product Goal

Build a working prototype that demonstrates:

1. A full raw → feature → forecast → risk → recommendation ML pipeline.
2. An honest dashboard: all numbers come from the pipeline, none are hardcoded.
3. Serverless deployability on Vercel with Neon Postgres.
4. Portfolio-ready code quality, testing, and documentation.

---

## Constraints

- **No real customer data** — only synthetic mock data (seed=42, reproducible).
- **No real purchase orders** — recommendations are internal suggestions only.
- **No real supplier communication** — no emails, webhooks, or ERP calls.
- **Serverless budget** — the demo pipeline must complete within Vercel's 60s timeout
  in small mode (10 products, 2 stores, 180 days).
- **Single developer, 11 sprints** — each sprint adds one well-defined capability.

---

## Why Synthetic Raw Data Was Used

DemandOS uses synthetic commerce records rather than fake dashboard outputs.
This is a deliberate design choice:

- **Mock data is raw operational data, not fake metrics.** The connector generates
  realistic orders, inventory snapshots, promotions, and purchase orders — records
  that would exist in a real ERP or e-commerce platform.
- **All derived values are computed by the pipeline.** MAE, WAPE, risk tiers,
  safety stock, and reorder quantities are calculated from the raw records, not
  invented. This proves the pipeline works end-to-end.
- **Reproducibility.** Using `seed=42` ensures the same data every time, making
  demo results consistent and verifiable.

---

## Architecture Overview

```
Connector (MockCommerceConnector)
    → raw_* tables (Postgres)
        → IngestionService + ValidationService
            → *_clean tables, sales_daily, inventory_daily, product_store_daily
                → AggregationService
                    → feature_matrix (36 leakage-safe columns)
                        → FeatureService
                            → ForecastRun, Forecast, ModelMetric
                                → ForecastingService (baselines)
                                → TrainingService (HistGradientBoosting)
                                    → StockoutRisk, StockoutRiskRun
                                        → StockoutService
                                            → ReorderRecommendation, RecommendationRun
                                                → RecommendationService
                                                    → FastAPI → Next.js Dashboard
```

---

## Data Pipeline

| Stage | Service | Tables Written |
|-------|---------|----------------|
| Ingestion | IngestionService + ValidationService | raw_products, raw_stores, raw_orders, raw_inventory_snapshots, raw_promotions, raw_suppliers, raw_purchase_orders |
| Aggregation | AggregationService | *_clean, sales_daily, inventory_daily, promotion_daily, product_store_daily |
| Feature Engineering | FeatureService | feature_matrix (36 columns) |
| Baseline Forecasting | ForecastingService | forecast_runs, forecasts, model_metrics |
| ML Training | TrainingService | model_versions, forecast_runs, forecasts, model_metrics |
| Planning Forecast | ForecastingService | forecast_runs (mode=forward_planning), forecasts |
| Stockout Risk | StockoutService | stockout_risk_runs, stockout_risks |
| Recommendations | RecommendationService | recommendation_runs, reorder_recommendations |

---

## Forecasting Approach

**Baseline models (rule-based):**
- Seasonal naive: `forecast(D) = lag_units_7d` (last same weekday)
- Moving average 7d: `forecast(D) = rolling_units_mean_7d`
- Moving average 28d: `forecast(D) = rolling_units_mean_28d`
- Heuristic ±1σ bands for p10/p90 (not calibrated probabilistic intervals)

**ML model:**
- Algorithm: `HistGradientBoostingRegressor` (scikit-learn) — handles missing values natively
- Global model: trained across all (product, store) series
- 30 leakage-safe features: lag, rolling, calendar, promo, price/margin, inventory, lifecycle
- OrdinalEncoder with sorted categories for deterministic encoding
- Train/test split by date; test = last `backtest_days` of feature matrix
- Predictions clipped at 0; ±1σ heuristic p10/p90

**Leakage prevention:**
- All lag and rolling features use `shift(1)` before rolling to ensure the window
  ends at D-1 (no same-day leakage)
- Pre-launch rows (days_since_launch < 0) are excluded from the training set
- `target_units_sold` is the supervised label — it is never an input feature

**Honest reporting:**
- The ML model is compared against baselines; it is not forced to win
- WAPE, MAE, RMSE, SMAPE, and Bias are reported per overall / category / store
- Metrics with zero denominators return `null` instead of infinity

---

## Stockout Risk Approach

Inputs:
- Current inventory from `inventory_daily` (latest snapshot on/before `as_of_date`)
- Inbound POs (status: submitted/confirmed) within the horizon window
- Supplier lead time from `raw_suppliers.lead_time_days_max`
- Forecast demand: `sum(p50_units)` and `sum(p90_units)` over horizon

Computed:
- `projected_end_inventory_p50 = current_available + inbound - demand_p50`
- `projected_end_inventory_p90 = current_available + inbound - demand_p90`
- `days_until_stockout` (null when no projected stockout within horizon)
- `safety_stock = 1.65 × rolling_std_7d × √lead_time`
- `inventory_coverage_ratio = current_available / (average_daily_forecast × lead_time)`
- `lost_sales_units_estimate`, `lost_sales_value_estimate`

Risk tier (deterministic rules):
- `critical`: days_until_stockout ≤ lead_time OR projected_p50 ≤ 0
- `high`: projected_p50 ≤ safety_stock OR coverage_ratio < 1.0
- `medium`: projected_p90 ≤ safety_stock OR coverage_ratio < 1.5
- `low`: well-covered inventory
- `unknown`: insufficient data

---

## Reorder Recommendation Safety Boundary

**What DemandOS does:**
- Computes a recommended order quantity using EOQ-adjacent formulas
- Assigns urgency (critical/high/medium/low)
- Generates a human-readable recommendation reason
- Assigns a confidence level based on data completeness
- Allows operators to review, approve, or ignore recommendations via the dashboard

**What DemandOS does NOT do:**
- Create real purchase orders
- Transmit orders to suppliers
- Send emails or Slack notifications
- Trigger any automatic purchasing action

Approved recommendations remain in the `approved_internal` status — they are
approved inside DemandOS only. No external action is taken.

---

## Dashboard Walkthrough

| Page | What it shows |
|------|--------------|
| Home | Raw counts (products, stores, orders, snapshots), pipeline status, risk/rec summary |
| Overview | KPI summary with honest pipeline readiness indicators |
| Forecasts | Forecast explorer with product selector and line chart (p10/p50/p90) |
| Inventory Risk | Risk queue ranked by tier; sortable by tier/store/category |
| Recommendations | Reorder queue with urgency, units, cost, action status |
| Model Performance | ML vs baseline comparison; WAPE/MAE/RMSE honesty |
| Data Health | Raw + canonical table counts, check list, run history |
| Pipeline Controls | Step-by-step pipeline controls; full pipeline run with durable run log |
| Product Drilldown | Per-product forecast chart + risk per store + recommendations |

---

## Deployment Architecture

```
Vercel Project (single project, repo root)
├── / → apps/web (Next.js, @vercel/next)
└── /api/* → api/index.py (FastAPI, @vercel/python)
              └── imports app.main (apps/api/app/main.py)
                  └── Neon Postgres (DATABASE_URL via Marketplace)
```

**Key environment variables:**

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Injected by Neon Marketplace |
| `DEMANDOS_API_KEY` | Write endpoint guard (set in Vercel panel) |
| `DEMANDOS_RUNTIME_MODE` | `vercel` |
| `DEMANDOS_DEMO_SCALE` | `small` |
| `NEXT_PUBLIC_API_BASE_URL` | (left unset for same-origin calls) |

**Serverless limitations acknowledged:**
- Model artifacts written to `/tmp` are ephemeral; `ModelVersion.artifact_path = "vercel_ephemeral"` documents this
- No background jobs; pipeline runs synchronously within a single request
- Cold starts may be slow on first request after inactivity

---

## Testing and Reliability

- **676 backend tests** across 15 test files (pytest)
- Tests use SQLite in-memory with StaticPool — no external DB needed for CI
- `test_raw_data_rule.py` enforces the raw-data-only connector contract
- `test_connector_contract.py` enforces connector output schemas
- `test_api_key_guard.py` verifies write endpoint protection
- `test_vercel_deployment.py` verifies single-project adapter wiring
- GitHub Actions CI: backend (pytest + verify.sh), frontend (npm build), repo hygiene
- Dependabot: GitHub Actions, pip, npm
- `scripts/verify.sh`: 100+ structural checks (files, schemas, migrations, adapter, docs)
- `scripts/smoke_production.py`: 15-check deployed endpoint validation

---

## Key Screenshots to Include

1. `/api/readiness` JSON response — proves Vercel + Neon connection
2. Home dashboard with populated KPIs — products, orders, risk, recommendations
3. Pipeline Controls showing completed run log
4. Forecasts page with line chart (p10/p50/p90 bands)
5. Inventory Risk page showing risk tiers (critical/high/medium/low)
6. Recommendations page with urgency queue and order cost estimates
7. Model Performance page showing ML vs baseline WAPE comparison
8. Data Health page with all checks passing
9. Product drilldown for a specific product
10. Vercel deployment overview (no secrets visible)
11. Neon database connection view (no secrets visible)
12. GitHub Actions CI passing

---

## What Is Intentionally Not Implemented

| Feature | Reason |
|---------|--------|
| Real Shopify/WooCommerce/ERP connectors | Requires API credentials; out of scope for portfolio MVP |
| Real purchase order creation | Safety boundary — recommendations are internal only |
| Email/Slack notifications | External side effects; excluded by design |
| User accounts / JWT auth | Overkill for single-operator demo |
| Model monitoring / drift detection | Sprint 12+ roadmap |
| Calibrated probabilistic intervals | p10/p90 are ±1σ heuristics, documented as such |
| Background schedulers (cron) | Serverless constraint; out of scope |
| Multi-tenant support | Single-operator demo |

---

## Future Roadmap

**Sprint 12 (planned):**
- Final portfolio screenshots
- Finalize case study assets
- Polish public README
- Architecture diagrams
- Final deployed smoke test
- Mark MVP complete

**Beyond Sprint 12:**
- CsvCommerceConnector (real file parsing)
- ShopifyConnector (Admin API integration)
- Calibrated prediction intervals (conformal prediction)
- Model monitoring and drift detection
- Dedicated backend on Render/Railway/Fly.io (Option B separation)
- User accounts with scoped permissions
- Automated pipeline scheduling

---

## Final Status

**DemandOS is a portfolio prototype.**

- All pipeline stages are implemented and working end-to-end.
- Deployed and reachable at `https://demand-os-three.vercel.app`.
- All dashboard pages show real computed data — no hardcoded metrics.
- 676 backend tests passing; frontend build passing; CI green.
- Production smoke script passes against the deployed URL.

This is not a production inventory management system. It is an honest, well-engineered
demonstration of what a real demand forecasting platform looks like under the hood.
