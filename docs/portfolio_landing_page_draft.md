# DemandOS — Portfolio Landing Page Draft

_Ready-to-adapt draft for a personal portfolio site. Paste into your preferred CMS or static site generator._

---

## Hero

**DemandOS**  
*Demand forecasting and inventory risk — built from scratch in 12 sprints.*

[View Live Demo](https://demand-os-three.vercel.app) · [Read Case Study](https://github.com/RaulMermans/demand-OS/blob/main/docs/case_study.md) · [GitHub](https://github.com/RaulMermans/demand-OS)

---

## What It Does

DemandOS answers three inventory questions for e-commerce retailers:

1. **How much will I sell?** — 28-day demand forecasts per SKU per store
2. **What will run out?** — Stockout risk scores with days-until-stockout
3. **What should I reorder?** — Quantity recommendations with estimated cost

Every number on the dashboard is computed by the pipeline from raw data.
No hardcoded metrics. No fake outputs.

---

## The Problem

Retail operations teams often have all the raw data they need — orders, inventory
snapshots, purchase orders — but lack the tooling to turn it into actionable decisions.
Spreadsheets don't scale. Off-the-shelf BI tools require pre-aggregated data.

I wanted to build a reference implementation of what this class of system looks like
under the hood: a full pipeline from raw ingestion to reorder recommendations,
with honest backtesting and an interactive dashboard.

---

## The Solution

A deterministic ML pipeline deployed on Vercel with Neon Postgres:

```
Raw Data → Aggregation → Feature Engineering → Forecasting
→ Stockout Risk → Reorder Recommendations → Dashboard
```

- **No LLM at inference time.** The pipeline is code-defined and deterministic.
- **No hardcoded outputs.** Every metric is computed from raw records.
- **No external side effects.** Recommendations are internal suggestions — no purchase orders are created.

---

## Architecture

```
Browser → Vercel Next.js → Vercel FastAPI → Neon Postgres
                                ↓
                    Deterministic ML Pipeline
                    (8 stages, sequential, each
                     reads + writes to Postgres)
```

**Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, scikit-learn (HistGradientBoosting),
pandas, Next.js 14, TypeScript, recharts, Vercel, Neon Postgres.

---

## Screenshots

| Home Dashboard | Forecasts | Inventory Risk |
|---|---|---|
| ![Home](https://raw.githubusercontent.com/RaulMermans/demand-OS/main/docs/screenshots/02-home-dashboard.png) | ![Forecasts](https://raw.githubusercontent.com/RaulMermans/demand-OS/main/docs/screenshots/04-forecasts.png) | ![Risk](https://raw.githubusercontent.com/RaulMermans/demand-OS/main/docs/screenshots/05-inventory-risk.png) |

| Recommendations | Model Performance | Data Health |
|---|---|---|
| ![Recs](https://raw.githubusercontent.com/RaulMermans/demand-OS/main/docs/screenshots/06-recommendations.png) | ![Model](https://raw.githubusercontent.com/RaulMermans/demand-OS/main/docs/screenshots/07-model-performance.png) | ![Health](https://raw.githubusercontent.com/RaulMermans/demand-OS/main/docs/screenshots/08-data-health.png) |

---

## Technical Highlights

- **Leakage-safe feature engineering:** All lag and rolling features use `shift(1)` before
  the rolling window, ensuring the feature for day D uses only data from days D-7 through D-1.
- **Global ML model:** One HistGradientBoosting model trained across all (product, store) series,
  learning cross-series patterns (category, seasonality, promotions) without overfitting to
  individual series with limited history.
- **Honest backtesting:** WAPE, MAE, RMSE, SMAPE, and Bias reported per model — the ML model
  is not forced to outperform baselines. Metrics with zero denominators return `null`.
- **Deterministic risk tiers:** Stockout risk is a set of deterministic rules on projected
  inventory, not a black-box score. Every rule is readable and testable.
- **EOQ-adjacent reorder formulas:** Safety stock, reorder point, and recommended units are
  computed from supplier lead times, demand variability, and forecast — not heuristics.
- **API key guard:** Write endpoints require `X-DemandOS-API-Key` when the env var is set.
  The key is stored in sessionStorage only (not localStorage, not cookies).

---

## Reliability and Safety

| Aspect | Detail |
|--------|--------|
| Backend tests | 709 passing (pytest, SQLite in-memory — no external DB needed for CI) |
| Structural checks | 100+ via `scripts/verify.sh` |
| Production smoke | 18-check script validates the live deployment |
| Raw-data enforcement | `test_raw_data_rule.py` runs on every CI push |
| CI | GitHub Actions: backend, frontend, repo-hygiene |
| No purchase orders | Safety boundary — no external actions from recommendations |
| No secrets in DB | API key never logged or stored in database |

---

## Demo

The live demo is pre-populated with synthetic retail data (seed=42, reproducible):

- 10 products × 2 stores × 180 days
- 1,677 orders, 1,156 inventory snapshots
- 946 baseline forecast rows, 560 planning forecast rows
- 20 stockout risk scores, 10 reorder recommendations

[Open the live demo →](https://demand-os-three.vercel.app)

> **Note:** The demo pipeline can be re-run from `/pipeline` using an API key.
> The app is read-only without one — all dashboard pages are publicly accessible.

---

## What I Would Improve Next

1. **Calibrated prediction intervals** — replace the ±1σ heuristic p10/p90 with
   conformal prediction for statistically valid coverage guarantees.
2. **Real connectors** — `CsvCommerceConnector` for file uploads, `ShopifyConnector`
   for Admin API ingestion of real order and inventory data.
3. **Model monitoring** — drift detection on input feature distributions and output
   forecast error trends, surfaced in the Data Health page.
4. **Dedicated backend** — move off Vercel's 60s function timeout to Render/Railway/Fly.io
   to support full-scale data (50 products × 5 stores × 730 days).
5. **Scheduled pipeline** — Celery + Redis (or Temporal) to run the pipeline nightly
   on fresh data without manual triggering.
