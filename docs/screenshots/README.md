# DemandOS — Screenshots

This directory is intended for portfolio case study screenshots.
Screenshots are not committed to the repository by default (they can be large).

## Suggested Screenshots

Capture the following pages after running the full demo pipeline:

| File | Page | What to show |
|------|------|-------------|
| `01_overview.png` | `/overview` | KPI cards, risk summary, recommendation count |
| `02_pipeline.png` | `/pipeline` | Completed full pipeline run with step statuses |
| `03_forecasts.png` | `/forecasts` | Forecast chart for a bestseller product |
| `04_risk_queue.png` | `/risks` | Risk queue with critical/high rows highlighted |
| `05_recommendations.png` | `/recommendations` | Reorder recommendations table with urgency badges |
| `06_model_performance.png` | `/model-performance` | ML vs baseline WAPE comparison |
| `07_data_health.png` | `/data-health` | Green checkmarks, canonical table counts |
| `08_product_drilldown.png` | `/products/{id}` | Single product — forecast chart + risk + recommendations |
| `09_vercel_deployed.png` | Vercel deployment | Frontend dashboard running on the Vercel URL |

## How to Capture

1. Run the full pipeline: http://localhost:3000/pipeline → **Run Full Demo Pipeline**
2. Navigate to each page above.
3. Use your OS screenshot tool or browser DevTools (Device Toolbar → 1440px wide).
4. Save to this directory.

## Notes

- Keep screenshots under 500KB each (compress with `pngquant` or similar).
- Do not commit screenshots containing real customer data.
- The mock connector produces deterministic data with `seed=42`.
