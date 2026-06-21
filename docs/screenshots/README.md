# DemandOS — Screenshots

This directory stores portfolio case study screenshots.
Capture these after running the full demo pipeline on the deployed Vercel app.

For the full screenshot specification, see `docs/case_study_assets.md`.

---

## Screenshot List

| Filename | URL | What it proves |
|----------|-----|----------------|
| `01_readiness.png` | `/api/readiness` | Vercel deployed, Neon connected, no secrets exposed |
| `02_home_populated.png` | `/` | Live KPIs from pipeline; runtime indicator in sidebar |
| `03_pipeline_completed.png` | `/pipeline` | All 8 pipeline steps completed with timestamps |
| `04_forecasts.png` | `/forecasts` | Product forecast chart with p10/p50/p90 bands |
| `05_inventory_risk.png` | `/risks` | Risk queue with Critical/High/Medium/Low tiers |
| `06_recommendations.png` | `/recommendations` | Reorder queue with urgency labels and cost estimates |
| `07_model_performance.png` | `/model-performance` | Honest ML vs baseline WAPE/MAE comparison |
| `08_data_health.png` | `/data-health` | Table counts and check list — all passing |
| `09_product_drilldown.png` | `/products/{id}` | Per-product forecast + risk + recommendations |
| `10_vercel_deployment.png` | Vercel dashboard | Single-project deployment overview (no secrets) |
| `11_neon_connection.png` | Vercel Storage panel | Neon Postgres integration confirmed (connection string blurred) |
| `12_ci_passing.png` | GitHub Actions | Backend + frontend + hygiene jobs all green |

---

## How to Capture

1. Ensure the deployed app is live at `https://demand-os-three.vercel.app`.
2. Run the full pipeline: go to `/pipeline` → enter API key → click **Run Full Demo Pipeline**.
3. Wait for all 8 steps to complete (~30–45 seconds in small mode).
4. Navigate to each page listed above and capture a screenshot.
5. For Vercel and Neon screenshots: log in to the Vercel dashboard and blur or crop out
   any API keys, database connection strings, or personal tokens before saving.
6. Save files to this directory with the filenames above.

---

## Notes

- Preferred width: 1440px (standard desktop). Use browser DevTools → Device Toolbar if needed.
- Keep files under 500KB each. Compress with `pngquant` or TinyPNG if needed.
- **Never include secrets, API keys, or database URLs in screenshots.**
- Screenshots are gitignored by default. Add them manually if you want to include them.
- The mock connector uses `seed=42` — results are deterministic and reproducible.

---

## Pre-Capture Checklist

- [ ] `/api/readiness` returns `"ready": true`
- [ ] Home page shows nonzero product and order counts
- [ ] All 8 pipeline steps are in `completed` status
- [ ] Forecasts page shows a line chart for at least one product
- [ ] Risk page shows rows with tier badges
- [ ] Recommendations page shows open rows
- [ ] Model performance shows ML vs baseline comparison
- [ ] Data health shows all checks passed
