# DemandOS — Demo Runbook

This guide walks through running the complete DemandOS demo from a clean checkout to a populated,
interactive dashboard.

---

## What DemandOS Demonstrates

DemandOS is a deterministic demand forecasting and inventory risk platform.
The demo shows:

1. **Raw data ingestion** — synthetic commerce records seeded with a fixed random seed.
2. **Aggregation** — canonical daily sales, inventory, and promotion tables.
3. **Feature engineering** — leakage-safe ML feature matrix.
4. **Baseline forecasting** — seasonal naive model with MAE/RMSE/WAPE metrics.
5. **ML forecasting** — HistGradientBoosting across all SKU/store series.
6. **Stockout risk scoring** — per-product/store risk tier and days-until-stockout.
7. **Reorder recommendations** — deterministic EOQ-based suggestions, human-approved only.
8. **Interactive dashboard** — real-time charts, pipeline controls, product drilldown.

---

## Prerequisites

```bash
# Python 3.11+ and Node 18+
cd apps/api && pip install -e ".[dev]"
cd apps/web && npm ci
```

---

## Local Setup

### 1. Start the backend

```bash
cd apps/api
uvicorn app.main:app --reload
# API available at http://localhost:8000
```

### 2. Start the frontend

```bash
cd apps/web
npm run dev
# Dashboard at http://localhost:3000
```

---

## Running the Demo

### Option A — Full Pipeline via UI (recommended for demos)

1. Open http://localhost:3000/pipeline
2. Enter your API key in the API Key field (if configured; skip in local dev).
3. Click **Run Full Demo Pipeline** and confirm the prompt.
4. Watch step-by-step progress in the durable run panel.
5. When complete, use the quick navigation links to explore results.

### Option B — Full Pipeline via API

```bash
curl -X POST http://localhost:8000/api/demo/run-full-pipeline \
  -H "Content-Type: application/json" \
  -d '{"seed": 42, "product_count": 50, "store_count": 5, "history_days": 730}'
```

Check the result:
```bash
curl http://localhost:8000/api/demo/pipeline-runs/latest
```

### Option C — Step-by-step via API

Run each step manually in order:

```bash
curl -X POST http://localhost:8000/api/demo/reset
curl -X POST http://localhost:8000/api/aggregation/run
curl -X POST http://localhost:8000/api/features/build
curl -X POST http://localhost:8000/api/forecasts/baseline/run \
  -H "Content-Type: application/json" \
  -d '{"model_type": "seasonal_naive", "horizon_days": 28, "backtest_days": 56}'
curl -X POST http://localhost:8000/api/models/train \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "hist_gradient_boosting", "horizon_days": 28, "backtest_days": 56}'
curl -X POST http://localhost:8000/api/forecasts/planning/run \
  -H "Content-Type: application/json" \
  -d '{"model_type": "seasonal_naive", "horizon_days": 28}'
curl -X POST http://localhost:8000/api/risks/run \
  -H "Content-Type: application/json" \
  -d '{"horizon_days": 28, "mode": "forward_planning"}'
curl -X POST http://localhost:8000/api/recommendations/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Expected Successful Outputs

After a successful full pipeline run (50 products, 5 stores, 730 days):

| Step | Expected output |
|------|----------------|
| Reset | ~80k–150k orders, ~182.5k inventory snapshots |
| Aggregation | ~182.5k product_store_daily rows |
| Features | ~180k+ feature_matrix rows |
| Baseline forecast | 224+ forecast rows, seasonal_naive metrics |
| ML training | HistGBM model artifact saved, 224+ forecast rows |
| Planning forecast | 28-day forward-looking forecast rows |
| Stockout risk | Up to 250 risk rows (50 products × 5 stores) |
| Recommendations | Up to 200+ recommendation rows |

---

## Pages to Inspect

After the pipeline completes:

| URL | What to show |
|-----|-------------|
| `/overview` | KPI summary: risk counts, recommendation cost, forecast readiness |
| `/pipeline` | Pipeline run history, step-by-step status |
| `/forecasts` | Forecast explorer — product selector + line chart |
| `/risks` | Risk queue — critical/high/medium/low tiers, sortable |
| `/recommendations` | Reorder recommendations — urgency, cost, action status |
| `/model-performance` | ML vs baseline comparison, WAPE/MAE/RMSE |
| `/data-health` | Raw + canonical table counts, pipeline checks |
| `/products/{id}` | Per-product drilldown — forecast + risk + recommendations |

---

## Vercel Frontend Deployment

The frontend dashboard can be deployed to Vercel independently of the backend.

See `docs/deployment.md` for full deployment instructions.

**Quick start:**

```bash
cd apps/web
vercel  # deploy to preview
vercel --prod  # deploy to production
```

Set `NEXT_PUBLIC_API_BASE_URL` to your deployed backend URL in the Vercel project environment variables.

---

## Common Errors and Fixes

| Error | Fix |
|-------|-----|
| `401 Invalid or missing X-DemandOS-API-Key` | Enter the key in the `/pipeline` page API Key field, or unset `DEMANDOS_API_KEY` in backend `.env` |
| `No raw orders found — reset step may have failed` | Run the Reset step first, then Aggregation |
| `No feature_matrix rows` | Aggregation must complete before features |
| `No forward_planning forecast found` | Run Planning Forecast before Stockout Risk |
| `Frontend CORS error` | Ensure `CORS_ORIGINS` in backend `.env` includes `http://localhost:3000` |
| `Feature build returns 0 rows` | Check that product_store_daily has rows: `GET /api/aggregation/status` |
| `ML training fails with too few samples` | Use at least 4 products, 2 stores, 91 days for the demo |

---

## Notes

- The demo uses fully synthetic data seeded with `seed=42` for reproducibility.
- No real customer data is ever used.
- No external API calls are made during the demo.
- No purchase orders are created — recommendations are suggestions only.
- The API key guard is disabled by default (empty `DEMANDOS_API_KEY`).
