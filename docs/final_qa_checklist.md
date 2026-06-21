# DemandOS — Final QA Checklist

Use this checklist before declaring a sprint or release complete.
Run through it top-to-bottom against the deployed Vercel app and local dev.

---

## A. Deployment Checks

- [ ] Deployed app loads at `https://demand-os-three.vercel.app`
- [ ] `/api/readiness` returns `"ready": true`
- [ ] `/api/readiness` returns `"runtime_mode": "vercel"`
- [ ] `/api/readiness` returns `"demo_scale": "small"`
- [ ] `/api/readiness` does NOT expose `DATABASE_URL` value
- [ ] `/api/readiness` does NOT expose `DEMANDOS_API_KEY` value
- [ ] `/api/runtime/check` returns runtime info without secrets
- [ ] Neon Postgres is connected (confirmed via `/api/readiness` `"database": "connected"`)
- [ ] Vercel environment variables are set (`DEMANDOS_API_KEY`, `DEMANDOS_RUNTIME_MODE`, `DEMANDOS_DEMO_SCALE`)

---

## B. Pipeline Execution Checks

- [ ] Full pipeline completes via `/pipeline` → Run Full Demo Pipeline
- [ ] Pipeline produces nonzero product count (expected: 10 in small mode)
- [ ] Pipeline produces nonzero order count (expected: ~1,677 in small mode)
- [ ] Pipeline produces nonzero inventory snapshot count (expected: ~1,156 in small mode)
- [ ] Feature matrix is populated (expected: ~1,154 rows in small mode)
- [ ] Baseline forecast rows are present (expected: ~946 in small mode)
- [ ] Planning forecast rows are present (expected: ~560 in small mode)
- [ ] Stockout risk rows are present (expected: 20 in small mode)
- [ ] Reorder recommendations are present (expected: 10 in small mode)

---

## C. Dashboard Pages

- [ ] Home (`/`) — KPI cards show nonzero counts; pipeline status rows present
- [ ] Overview (`/overview`) — summary stats loaded from API
- [ ] Forecasts (`/forecasts`) — product selector works; line chart renders with p10/p50/p90
- [ ] Inventory Risk (`/risks`) — risk queue shows multiple rows with tier badges
- [ ] Recommendations (`/recommendations`) — reorder queue shows urgency and cost
- [ ] Model Performance (`/model-performance`) — ML vs baseline comparison visible
- [ ] Data Health (`/data-health`) — table counts and check list loaded
- [ ] Pipeline Controls (`/pipeline`) — step list and durable run log visible
- [ ] Product Drilldown (`/products/{id}`) — forecast chart + risk + recommendations for a product

---

## D. Security Checks

- [ ] No secrets exposed in any API response body (smoke script check 14)
- [ ] No database URL or SQLite path in any API response (smoke script check 15)
- [ ] `DEMANDOS_API_KEY` is not returned in any read-only endpoint response
- [ ] Sidebar runtime indicator shows runtime mode without exposing secrets
- [ ] API key stored in `sessionStorage` only (not `localStorage`, not `document.cookie`)
- [ ] No `.env` file committed to the repository
- [ ] No real customer data committed to `data/`
- [ ] No model artifacts committed to the repository (`*.joblib` is gitignored)

---

## E. API Key Guard

- [ ] POST endpoints return `401` when `DEMANDOS_API_KEY` is set and header is missing
- [ ] POST endpoints accept correct key in `X-DemandOS-API-Key` header
- [ ] GET (read-only) endpoints are always accessible without a key
- [ ] Guard disabled when `DEMANDOS_API_KEY` env var is empty (local dev)

---

## F. Error States and Empty States

- [ ] Home page shows "No data yet" banner when pipeline hasn't run
- [ ] Empty state on `/risks` links to Pipeline Controls
- [ ] Empty state on `/recommendations` links to Pipeline Controls
- [ ] Error state shows `isApiKeyError` hint when 401 is received
- [ ] Error state distinguishes "backend unavailable" from "no data"
- [ ] No raw stack traces visible in normal UI (only in expandable debug blocks if any)

---

## G. No External Side Effects

- [ ] No purchase orders created during pipeline run
- [ ] No emails sent during pipeline run
- [ ] No Slack webhooks triggered during pipeline run
- [ ] No external HTTP calls made by the pipeline services (verified by test suite)
- [ ] `PATCH /api/recommendations/{id}/status` does not create external purchase orders

---

## H. Documentation

- [ ] `docs/case_study.md` exists and is up to date
- [ ] `docs/demo_script.md` exists and is ready for presenter use
- [ ] `docs/case_study_assets.md` exists with screenshot list
- [ ] `docs/final_qa_checklist.md` exists (this file)
- [ ] `docs/deployment.md` documents single Vercel project mode
- [ ] `docs/demo_runbook.md` documents Vercel demo flow
- [ ] `docs/operator_runbook.md` documents Vercel operator instructions
- [ ] `docs/sprint_plan.md` reflects Sprint 11 completion

---

## I. Test Suite

- [ ] `cd apps/api && pytest` — all tests pass
- [ ] `bash scripts/verify.sh` — all checks pass
- [ ] `cd apps/web && npm run build` — frontend build succeeds (no TypeScript errors)
- [ ] `python scripts/smoke_production.py --base-url https://demand-os-three.vercel.app` — passes

---

## J. Vercel Environment Variables

Confirm these are set in the Vercel project → Settings → Environment Variables:

| Variable | Expected Value |
|----------|----------------|
| `DEMANDOS_API_KEY` | A strong random string (not exposed here) |
| `DEMANDOS_RUNTIME_MODE` | `vercel` |
| `DEMANDOS_DEMO_SCALE` | `small` |
| `DATABASE_URL` | Injected by Neon Marketplace (do not set manually) |
| `NEXT_PUBLIC_API_BASE_URL` | (must be left unset for same-origin calls) |

---

## K. Smoke Script

Run the production smoke check:

```bash
python scripts/smoke_production.py \
  --base-url https://demand-os-three.vercel.app
```

Expected: all 15 checks pass.

With API key and pipeline run:

```bash
python scripts/smoke_production.py \
  --base-url https://demand-os-three.vercel.app \
  --api-key "$DEMANDOS_API_KEY" \
  --run-pipeline
```

---

## Sign-off

- [ ] All sections above are checked
- [ ] Screenshots captured and saved to `docs/screenshots/`
- [ ] Sprint plan updated
- [ ] Commit created and pushed to main
- [ ] Deployment verified post-push
