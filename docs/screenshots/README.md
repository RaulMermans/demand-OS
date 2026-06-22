# DemandOS — Public Portfolio Screenshots

Application screenshots are captured against the deployed demo with:

```bash
python scripts/capture_screenshots.py \
  --base-url https://demand-os-three.vercel.app
```

## Screenshot Status

| # | Filename | Page / source | Status |
|---|---|---|---|
| 1 | `01-readiness.png` | `/api/readiness` | ✅ Captured |
| 2 | `02-home-dashboard.png` | `/` | ✅ Captured |
| 3 | `03-pipeline-completed.png` | `/pipeline` | ✅ Captured |
| 4 | `04-forecasts.png` | `/forecasts` | ✅ Captured |
| 5 | `05-inventory-risk.png` | `/risks` | ✅ Captured |
| 6 | `06-recommendations.png` | `/recommendations` | ✅ Captured |
| 7 | `07-model-performance.png` | `/model-performance` | ✅ Captured |
| 8 | `08-data-health.png` | `/data-health` | ✅ Captured |
| 9 | `09-product-drilldown.png` | `/products/{productId}` | ✅ Captured |
| 10 | `10-vercel-deployment.png` | Vercel dashboard | ⏳ Manual |
| 11 | `11-neon-connection-redacted.png` | Neon/Vercel integration | ⏳ Manual |
| 12 | `12-ci-passing.png` | GitHub Actions | ⏳ Manual |
| 13 | `13-csv-upload.png` | `/csv-upload` | ✅ Captured |
| 14 | `14-monitoring.png` | `/monitoring` | ✅ Captured |
| 15 | `15-scenarios.png` | `/scenarios` | ✅ Captured |
| 16 | `16-connectors.png` | `/connectors` | ✅ Captured |
| 17 | `17-ml-insights.png` | `/data-science` | ⏳ Pending Sprint 15 deploy |

The application captures should show computed backend data where available. Empty
states are acceptable only when they clearly explain the next action.

## Manual Capture Instructions

### 10 — Vercel deployment

Capture the production deployment status and public domain. Crop out personal
account details and never expose environment-variable values.

### 11 — Neon connection

Capture only the integration/connection status. Blur or crop the complete database
connection string, host, username, password, and pooled URL. Save the redacted file
as `11-neon-connection-redacted.png`.

### 12 — CI passing

Capture the latest GitHub Actions run with backend, frontend, and repository-hygiene
jobs visible and green.

## Safety Rules

- Never show API keys, tokens, cookies, environment-variable values, or database URLs.
- Use synthetic data only; no personal or customer data may appear.
- Keep screenshots under roughly 250 KB where practical.
- Verify the browser address bar and visible console output before capture.
- Do not commit unredacted Vercel or Neon screenshots.

## Sprint 14 Capture Checklist

- [x] Refreshed visual system is deployed.
- [x] Read-only production smoke passes.
- [x] Screenshots 1–9 and 13–16 are recaptured from the refreshed deployment.
- [ ] Manual screenshots 10–12 are redacted and reviewed.
- [x] No secret values or connection strings are visible in automated captures.

## Sprint 15 Capture Checklist

- [ ] Deploy Sprint 15 to Vercel.
- [ ] Run `python scripts/capture_screenshots.py --base-url https://demand-os-three.vercel.app` to refresh automated captures.
- [ ] Manually capture `17-ml-insights.png` from `/data-science`.
- [ ] Refresh `02-home-dashboard.png`, `04-forecasts.png`, `05-inventory-risk.png`, `06-recommendations.png`, `07-model-performance.png`, `08-data-health.png` to show Sprint 15 UX improvements.
- [ ] Verify no secrets or connection strings are visible.

### 17 — ML Insights

Capture the `/data-science` page showing the ML workflow overview, model leaderboard,
forecast diagnostics, and feature signal groups. The data volume and business impact
cards should be visible. No secrets should appear.
