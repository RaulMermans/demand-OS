# DemandOS — Screenshots

This directory stores portfolio case study screenshots for Sprint 12 MVP closeout.
Captured via Playwright CLI against the deployed Vercel app (`https://demand-os-three.vercel.app`).

To recapture: `python scripts/capture_screenshots.py --base-url https://demand-os-three.vercel.app`

---

## Screenshot Status

| # | Filename | Page / Source | What it proves | Status |
|---|----------|---------------|----------------|--------|
| 1 | `01-readiness.png` | `/api/readiness` | Vercel deployed, Neon connected (`"ready": true`), no secrets in response | ✅ Captured |
| 2 | `02-home-dashboard.png` | `/` | Live KPI cards from pipeline — 10 products, 1,677 orders, risk/rec counts | ✅ Captured |
| 3 | `03-pipeline-completed.png` | `/pipeline` | All 8 pipeline steps completed with timestamps in durable run log | ✅ Captured |
| 4 | `04-forecasts.png` | `/forecasts` | Forecast line chart with p10/p50/p90 bands from real computed forecasts | ✅ Captured |
| 5 | `05-inventory-risk.png` | `/risks` | Risk queue with Critical/High/Medium/Low tier badges, days-until-stockout | ✅ Captured |
| 6 | `06-recommendations.png` | `/recommendations` | Reorder queue with urgency labels, recommended units, and estimated costs | ✅ Captured |
| 7 | `07-model-performance.png` | `/model-performance` | Honest ML vs baseline WAPE/MAE/RMSE comparison | ✅ Captured |
| 8 | `08-data-health.png` | `/data-health` | Table counts for all pipeline stages and health check list | ✅ Captured |
| 9 | `09-product-drilldown.png` | `/products/prod_008` | Per-product forecast chart + risk per store + recommendations | ✅ Captured |
| 10 | `10-vercel-deployment.png` | Vercel dashboard | Single-project deployment overview showing frontend + backend | ⏳ Manual capture required |
| 11 | `11-neon-connection.png` | Vercel Storage panel | Neon Postgres integration panel (connection string must be blurred) | ⏳ Manual capture required |
| 12 | `12-ci-passing.png` | GitHub Actions | Backend + frontend + hygiene CI jobs all green | ⏳ Manual capture required |

---

## Automated Capture (Screenshots 1–9)

Screenshots 1–9 were captured automatically using Playwright CLI:

```bash
python scripts/capture_screenshots.py --base-url https://demand-os-three.vercel.app
```

Captured: **2026-06-21** against `https://demand-os-three.vercel.app`.  
Pipeline state: full demo pipeline completed (small mode, seed=42).

---

## Manual Capture Instructions (Screenshots 10–12)

### 10 — Vercel Deployment Overview

1. Log in to vercel.com and open the DemandOS project.
2. Go to the **Deployments** tab.
3. Capture the deployment list showing the latest production deployment (green).
4. **Crop out** any personal API tokens or secret env var values.
5. Save as `10-vercel-deployment.png`.

### 11 — Neon Connection Panel

1. In the Vercel project, go to **Storage**.
2. Open the Neon Postgres integration.
3. Capture the panel showing the database is connected.
4. **Blur or crop** the full connection string (DATABASE_URL value).
5. Save as `11-neon-connection.png`.

### 12 — GitHub Actions CI Passing

1. Open the GitHub repository → **Actions** tab.
2. Open the latest workflow run.
3. Capture the run overview showing `backend`, `frontend`, and `repo-hygiene` jobs all green.
4. Save as `12-ci-passing.png`.

---

## Safety Notes

- **Never include API keys, database URLs, or personal tokens in screenshots.**
- The mock connector uses `seed=42` — results are deterministic and reproducible.
- File sizes: 20KB–120KB each (Playwright default quality). Compress with `pngquant` if needed.
