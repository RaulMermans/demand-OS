# DemandOS — Operator Runbook

This guide is for operators managing a running DemandOS instance.

---

## How to Reset Demo Data

**Via API:**
```bash
curl -X POST http://localhost:8000/api/demo/reset \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <your-key>" \
  -d '{"seed": 42, "product_count": 50, "store_count": 5, "history_days": 730}'
```

**Via script:**
```bash
cd apps/api
python scripts/seed_demo_data.py --seed 42 --products 50 --stores 5 --days 730
```

**Via UI:**
Go to `/pipeline` → click **Reset Demo Data** → confirm the prompt.

This deletes all raw, canonical, feature, forecast, risk, and recommendation data,
then re-seeds from the mock connector. The operation is idempotent.

---

## How to Run Each Pipeline Step Manually

Use the `/pipeline` page in the UI, or these API calls:

```bash
# Aggregation
curl -X POST http://localhost:8000/api/aggregation/run \
  -H "X-DemandOS-API-Key: <key>"

# Feature build
curl -X POST http://localhost:8000/api/features/build \
  -H "X-DemandOS-API-Key: <key>"

# Baseline forecast (seasonal_naive)
curl -X POST http://localhost:8000/api/forecasts/baseline/run \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <key>" \
  -d '{"model_type": "seasonal_naive", "horizon_days": 28, "backtest_days": 56}'

# ML model training
curl -X POST http://localhost:8000/api/models/train \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <key>" \
  -d '{"algorithm": "hist_gradient_boosting", "horizon_days": 28, "backtest_days": 56}'

# Planning forecast
curl -X POST http://localhost:8000/api/forecasts/planning/run \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <key>" \
  -d '{"model_type": "seasonal_naive", "horizon_days": 28}'

# Stockout risk
curl -X POST http://localhost:8000/api/risks/run \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <key>" \
  -d '{"horizon_days": 28, "mode": "forward_planning"}'

# Recommendations
curl -X POST http://localhost:8000/api/recommendations/run \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <key>" \
  -d '{}'
```

---

## How to Run the Full Demo Pipeline

**Via API (one call):**
```bash
curl -X POST http://localhost:8000/api/demo/run-full-pipeline \
  -H "Content-Type: application/json" \
  -H "X-DemandOS-API-Key: <key>" \
  -d '{"seed": 42, "product_count": 50, "store_count": 5, "history_days": 730}'
```

This runs all 8 steps in order, stops on first failure, and returns per-step status.

**Via UI:**
Go to `/pipeline` → click **Run Full Demo Pipeline** → confirm.

---

## How to Interpret Failed Steps

When a pipeline run fails:

```bash
curl http://localhost:8000/api/demo/pipeline-runs/latest
```

The response includes `steps` with per-step `status` and `error_message`.

Possible step statuses:
- `completed` — step succeeded
- `failed` — step raised an error; see `error_message`
- `skipped` — step was not attempted because a prior step failed
- `pending` — step has not started yet
- `running` — step is in progress

Common causes:
- `reset_demo` fails → insufficient disk space or DB lock
- `aggregation` fails → no raw orders (reset step may not have completed)
- `features` fails → no product_store_daily rows (aggregation not run)
- `baseline_forecast` fails → no feature_matrix rows (features not built)
- `train_ml` fails → insufficient training data (need ≥ 4 products, 2 stores, 90 days)
- `planning_forecast` fails → no feature_matrix or DB issue
- `stockout_risk` fails → no forward_planning forecast rows
- `recommendations` fails → no stockout risk run

---

## How the API Key Guard Works

The `DEMANDOS_API_KEY` environment variable controls access to all write/control endpoints.

**When `DEMANDOS_API_KEY` is empty (default):**
- Guard is disabled.
- All POST/PATCH endpoints are publicly accessible.
- Safe for local development.

**When `DEMANDOS_API_KEY` is set:**
- All POST/PATCH endpoints require the header:
  ```
  X-DemandOS-API-Key: <your-key>
  ```
- Missing or wrong key → 401 Unauthorized.
- The key is never logged, stored in the database, or returned in responses.

**In the UI:**
- The operator enters the key in the `/pipeline` page API Key field.
- It is stored in `sessionStorage` only (cleared when the tab is closed).
- It is never stored in `localStorage`, cookies, or environment variables.

---

## How the Frontend Connects to the Backend

The Next.js frontend reads `NEXT_PUBLIC_API_BASE_URL` at build time and runtime.

**Local development:**
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```
This is the default when no env var is set.

**Vercel/production:**
Set `NEXT_PUBLIC_API_BASE_URL` in the Vercel project environment variables panel
to the URL of the deployed backend service.

All API calls go through `apps/web/lib/api.ts`. There are no hardcoded backend URLs in
any component.

---

## What Actions Are Safe

These actions are always safe to run (idempotent, internal, no external effects):

- `POST /api/demo/reset` — re-seeds demo data
- `POST /api/aggregation/run` — rewrites canonical tables
- `POST /api/features/build` — rewrites feature matrix
- `POST /api/forecasts/baseline/run` — rewrites baseline forecasts
- `POST /api/models/train` — trains and saves a new model version
- `POST /api/forecasts/planning/run` — rewrites planning forecasts
- `POST /api/risks/run` — rewrites risk scores
- `POST /api/recommendations/run` — rewrites recommendations
- `POST /api/demo/run-full-pipeline` — runs all of the above in sequence
- `PATCH /api/recommendations/{id}/status` — updates recommendation review status

All these operations are:
- Fully internal to DemandOS
- Write to the local database only
- Idempotent (safe to re-run with the same parameters)

---

## What Actions Are Intentionally Not Implemented

The following are intentionally out of scope and will not be added:

- Real purchase order creation or transmission to suppliers
- Email or Slack notifications
- Automatic background scheduling (cron-based pipeline runs)
- Shopify/WooCommerce live API calls in the current connectors
- User accounts or JWT authentication
- Model monitoring or drift detection
- Multi-tenant support

---

## No External Side Effects Guarantee

DemandOS does not:

- Call any external HTTP endpoints during pipeline execution
- Send emails, webhooks, or Slack messages
- Create purchase orders in any ERP or procurement system
- Transmit data outside the local machine

This guarantee is enforced by the project's architecture and verified in the test suite.

---

## Vercel Single-Project Operator Instructions

When running in single Vercel project mode (`DEMANDOS_RUNTIME_MODE=vercel`):

### Required Environment Variables (Vercel Panel)

| Variable | Value |
|----------|-------|
| `DEMANDOS_API_KEY` | A strong random string |
| `DEMANDOS_RUNTIME_MODE` | `vercel` |
| `DEMANDOS_DEMO_SCALE` | `small` |
| `DATABASE_URL` | Injected automatically by Neon Marketplace |

`NEXT_PUBLIC_API_BASE_URL` must be **left unset** for same-origin calls.

### Check Readiness

```bash
curl https://<your-vercel-domain>/api/readiness
# Expected: {"ready": true, "status": "ok", "runtime_mode": "vercel", "demo_scale": "small", "reason": null}
```

If `ready` is `false`, check that `DATABASE_URL` is set to a Postgres URL (not SQLite).

### Run Demo Pipeline on Vercel

1. Go to `https://<your-vercel-domain>/pipeline`.
2. Enter your `DEMANDOS_API_KEY` in the API Key field.
3. Click **Run Full Demo Pipeline**.

With `DEMANDOS_DEMO_SCALE=small`, the pipeline runs 10 products × 2 stores × 180 days —
typically completes within 30–45 seconds.

### Model Artifact Limitation on Vercel

Vercel serverless functions have a read-only filesystem outside `/tmp`.
Model artifacts written to `/tmp` are **ephemeral** — they do not persist across invocations.
The `ModelVersion` row in Postgres records `artifact_path = "vercel_ephemeral"` to document this.
Forecast results and metrics are fully stored in Postgres and are durable.

To retrain a model, run the pipeline again — the new artifact is available for the
duration of that function invocation.

---

## Sprint 12 — MVP Deployment Status

**Deployed at:** https://demand-os-three.vercel.app  
**Runtime:** Vercel serverless + Neon Postgres  
**Scale:** `DEMANDOS_DEMO_SCALE=small` (10 products, 2 stores, 180 days)

### Production validation commands

```bash
# Read-only smoke (18 checks, no data mutation)
python scripts/smoke_production.py --base-url https://demand-os-three.vercel.app

# Full check with pipeline run (requires API key)
python scripts/smoke_production.py \
  --base-url https://demand-os-three.vercel.app \
  --api-key "$DEMANDOS_API_KEY" \
  --run-pipeline
```

### Known operational limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max pipeline scale | `small` (10 products, 2 stores, 180 days) | Vercel 60s function timeout |
| Model artifact persistence | None (ephemeral `/tmp`) | Vercel serverless filesystem |
| Concurrent pipeline runs | 1 (no queuing) | Single serverless function |
| Cold start time | 3–8 seconds | Lambda container warm-up |

### Safety guarantees (unchanged from Sprint 9)

- No real purchase orders are ever created
- No emails, Slack messages, or external notifications are sent
- No external HTTP calls are made by pipeline services
- `approved_internal` status = internal-only, no external action
- API key never logged or stored in database

### MVP sign-off

DemandOS MVP is complete as of Sprint 12 (2026-06-21).
All pipeline stages are implemented, tested, deployed, and validated.
