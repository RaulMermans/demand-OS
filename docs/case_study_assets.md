# DemandOS — Case Study Assets

Screenshots and supporting assets for the portfolio case study.

**Sprint 14 capture status:** core application screenshots exist from Sprint 12.
Screenshots 1–9 and 13–16 should be recaptured after the refreshed UI deploys.
Vercel, Neon, and GitHub views remain manual and must be redacted.

To recapture: `python scripts/capture_screenshots.py --base-url https://demand-os-three.vercel.app`

---

## Required Screenshots

### 1. `/api/readiness` — Deployment validation

**URL:** `https://demand-os-three.vercel.app/api/readiness`

**What to capture:** The JSON response in a browser or terminal.

**What it proves:**
- The Vercel deployment is live.
- Neon Postgres is connected (`"database": "connected"`).
- `"ready": true`, `"runtime_mode": "vercel"`, `"demo_scale": "small"`.
- No secrets are exposed in the response body.

**Filename:** `screenshots/01_readiness.png`

---

### 2. Home Dashboard — Populated

**URL:** `https://demand-os-three.vercel.app/`

**What to capture:** The home page with KPI cards showing nonzero counts and a
populated pipeline status panel.

**What it proves:**
- Products, orders, and inventory snapshots are seeded from the pipeline.
- Risk and recommendation counts are real computed values.
- The `"Data: Seeded"` runtime indicator is visible in the sidebar.

**Filename:** `screenshots/02_home_populated.png`

---

### 3. Pipeline Completed Run

**URL:** `https://demand-os-three.vercel.app/pipeline`

**What to capture:** The Pipeline Controls page with the durable run log showing
all 8 steps as `completed`.

**What it proves:**
- The full demo pipeline ran successfully end-to-end.
- Each step has a timestamp and `completed` status.
- The durable run record in Postgres is surfaced in the UI.

**Filename:** `screenshots/03_pipeline_completed.png`

---

### 4. Forecasts Page

**URL:** `https://demand-os-three.vercel.app/forecasts`

**What to capture:** A product selected in the dropdown, showing the line chart
with p10/p50/p90 forecast bands and actual units overlay.

**What it proves:**
- Forecasts are computed from the feature matrix and stored in Postgres.
- The line chart is driven by real API data, not hardcoded values.
- p10/p50/p90 bands are visible and distinct.

**Filename:** `screenshots/04_forecasts.png`

---

### 5. Inventory Risk Page

**URL:** `https://demand-os-three.vercel.app/risks`

**What to capture:** The risk queue showing multiple rows with tier badges
(Critical / High / Medium / Low), days-until-stockout, and coverage ratios.

**What it proves:**
- Stockout risk is scored per product/store pair.
- Risk tiers are deterministically computed from forecasts + inventory data.
- All values are live from the database.

**Filename:** `screenshots/05_inventory_risk.png`

---

### 6. Recommendations Page

**URL:** `https://demand-os-three.vercel.app/recommendations`

**What to capture:** The reorder recommendation queue showing urgency labels,
recommended units, estimated order cost, and action status (`open`).

**What it proves:**
- Reorder recommendations are computed from risk runs + product data.
- Estimated order cost is derived from unit cost × recommended quantity.
- Operators can review recommendations in the UI.

**Filename:** `screenshots/06_recommendations.png`

---

### 7. Model Performance Page

**URL:** `https://demand-os-three.vercel.app/model-performance`

**What to capture:** The model performance comparison showing ML vs baseline
WAPE/MAE/RMSE — with honest values (ML does not claim to always win).

**What it proves:**
- The training service runs HistGradientBoosting across all series.
- Metrics are real backtesting results stored in `model_metrics`.
- Baseline comparison is transparent and honest.

**Filename:** `screenshots/07_model_performance.png`

---

### 8. Data Health Page

**URL:** `https://demand-os-three.vercel.app/data-health`

**What to capture:** The Data Health page with table counts and a check list
showing all checks passed (green).

**What it proves:**
- Raw and canonical table counts are live from Postgres.
- Referential integrity checks are passing.
- The complete pipeline history is shown (ingestion, aggregation, features, forecasts, risk, recommendations).

**Filename:** `screenshots/08_data_health.png`

---

### 9. Product Drilldown

**URL:** `https://demand-os-three.vercel.app/products/{product_id}`

**What to capture:** A specific product page showing the forecast chart, risk
per store, and recommendations per store.

**What it proves:**
- The product drilldown page aggregates data from three pipeline stages.
- All data is product-specific and fetched from the API.

**Filename:** `screenshots/09_product_drilldown.png`

---

### 10. Vercel Deployment Overview

**Source:** Vercel dashboard — project overview page.

**What to capture:** The Vercel project page showing the deployment URL,
framework detected, and last deployment status. Crop out any API keys or tokens.

**What it proves:**
- The project is deployed from the GitHub repository root.
- Frontend and backend are served from a single Vercel project.

**Filename:** `screenshots/10_vercel_deployment.png`

---

### 11. Neon Connection View

**Source:** Vercel project → Storage → Neon connection panel.

**What to capture:** The Neon integration panel confirming the database is
connected. Crop out or blur the connection string.

**What it proves:**
- Neon Postgres is integrated via the Vercel Marketplace.
- `DATABASE_URL` is injected automatically.

**Filename:** `screenshots/11_neon_connection.png`

---

### 12. GitHub Actions CI Passing

**Source:** GitHub repository → Actions tab.

**What to capture:** The latest CI run showing backend, frontend, and
repo-hygiene jobs all green.

**What it proves:**
- Tests pass in CI on every push.
- The frontend build succeeds.
- No secrets or forbidden files are committed.

**Filename:** `screenshots/12_ci_passing.png`

---

### 13. CSV Upload

**URL:** `https://demand-os-three.vercel.app/csv-upload`

Capture the entity template guidance, raw-data-only notice, 2 MB limit, validation
summary, and upload-history area. Do not upload real data for the screenshot.

**Filename:** `screenshots/13-csv-upload.png`

### 14. Monitoring

**URL:** `https://demand-os-three.vercel.app/monitoring`

Capture green/yellow/red explanations, latest-vs-previous columns, and the
Run Monitoring control. No notification or external alert should be implied.

**Filename:** `screenshots/14-monitoring.png`

### 15. Scenario Planning

**URL:** `https://demand-os-three.vercel.app/scenarios`

Capture bounded inputs, the simulated/non-mutating label, before/after metrics,
and the top impacted product/store comparison.

**Filename:** `screenshots/15-scenarios.png`

### 16. Connectors

**URL:** `https://demand-os-three.vercel.app/connectors`

Capture Shopify/WooCommerce disabled status, credential requirements, dry-run
explanation, and the explicit no-live-API-call notice.

**Filename:** `screenshots/16-connectors.png`

---

## Pre-Screenshot Checklist

Before capturing screenshots:

- [ ] Full demo pipeline has run successfully (`/pipeline` → all 8 steps completed)
- [ ] `/api/readiness` returns `"ready": true`
- [ ] Products, orders, and inventory snapshots visible on home page
- [ ] At least one product has forecast data for drilldown screenshot
- [ ] Risks page shows multiple rows with different tiers
- [ ] Recommendations page shows open rows with urgency labels
- [ ] Model performance page shows both ML and baseline metrics
- [ ] Data health shows all checks passed
- [ ] All screenshots are cropped to remove window chrome where appropriate
- [ ] No API keys, database URLs, or personal tokens visible in any screenshot

---

## Asset Storage

Place screenshot files in `docs/screenshots/` with the filenames above.
Do not commit generated data, model artifacts, or `.env` files alongside screenshots.

---

## Sprint 12 Capture Summary

| # | Filename | Status | Captured |
|---|----------|--------|---------|
| 1 | `01-readiness.png` | ✅ Captured | 2026-06-21 via Playwright |
| 2 | `02-home-dashboard.png` | ✅ Captured | 2026-06-21 via Playwright |
| 3 | `03-pipeline-completed.png` | ✅ Captured | 2026-06-21 via Playwright |
| 4 | `04-forecasts.png` | ✅ Captured | 2026-06-21 via Playwright |
| 5 | `05-inventory-risk.png` | ✅ Captured | 2026-06-21 via Playwright |
| 6 | `06-recommendations.png` | ✅ Captured | 2026-06-21 via Playwright |
| 7 | `07-model-performance.png` | ✅ Captured | 2026-06-21 via Playwright |
| 8 | `08-data-health.png` | ✅ Captured | 2026-06-21 via Playwright |
| 9 | `09-product-drilldown.png` | ✅ Captured | 2026-06-21 via Playwright (prod_008) |
| 10 | `10-vercel-deployment.png` | ⏳ Pending | Manual — Vercel dashboard |
| 11 | `11-neon-connection.png` | ⏳ Pending | Manual — Vercel Storage panel |
| 12 | `12-ci-passing.png` | ⏳ Pending | Manual — GitHub Actions |
