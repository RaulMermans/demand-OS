# DemandOS Release Notes

## Project Status

DemandOS is a public portfolio prototype and portfolio MVP. It demonstrates an
internal-tool-style workflow for demand forecasting, stockout risk, and human-reviewed
reorder planning using synthetic raw operational data.

**Live demo:** https://demand-os-three.vercel.app

## What Works

- Deterministic raw → aggregate → feature → forecast → risk → recommendation pipeline
- Seasonal-naive, moving-average, and global HistGradientBoosting forecasting
- Backtesting and model comparison
- Product/store stockout risk and reorder recommendation calculations
- Dashboard, product drilldown, data-health checks, and protected pipeline controls
- Raw CSV validation/upload mode with a 2 MB prototype limit
- Model and data-health monitoring comparisons
- Simulated, non-mutating scenario planning
- Connector configuration validation and no-network dry runs

## What Is Simulated

- All demo commerce records are synthetic.
- Scenario outputs are simulated and stored separately.
- Forecast intervals are heuristic bands, not calibrated probability guarantees.
- Recommendation approval is internal workflow state only.

## What Is Intentionally Disabled

- Live Shopify and WooCommerce calls
- Real purchase-order creation
- Supplier communication, email, Slack, and webhooks
- Autonomous or scheduled purchasing
- Customer accounts and multi-tenant access

## Testing Summary

- Backend pytest suite: 451 unique tests passing
- Frontend type check and production build: passing (15 pages)
- `scripts/verify.sh`: 201 structural and safety checks passing
- `scripts/public_readiness_check.py`: secrets, database URLs, environment files,
  generated data/model artifacts, and duplicate-file audit
- `scripts/smoke_production.py`: read-only deployed endpoint and secret-leak validation

Final command results are recorded in [final_qa_checklist.md](final_qa_checklist.md).

## Known Limitations

- Vercel serverless execution limits the deployed demo to the small dataset.
- Model artifacts are ephemeral in the deployed serverless runtime.
- CSV ingestion is deliberately limited to 2 MB.
- Monitoring is on-demand and does not send alerts.
- Manual screenshots of Vercel, Neon, and CI require authenticated access and redaction.
- No repository license has been selected; absent a license, normal copyright rules apply.

## Future Roadmap

- Calibrated forecast intervals
- Persistent model-artifact storage
- Dedicated backend and scheduled pipeline runs
- Live connectors only after security, privacy, reliability, and approval controls
- Optional monitoring notifications behind explicit side-effect gates

## Public Release Checklist

- [x] Public README and case study updated
- [x] Sprint 13 advanced features documented honestly
- [x] Sprint 14 visual refresh implemented
- [x] Public-readiness audit added
- [x] Safety boundaries retained
- [x] Refreshed deployment validated
- [x] Updated automated screenshots captured
- [ ] Manual deployment/Neon/CI screenshots captured and redacted
- [ ] Maintainer selects a repository license if reuse is intended

## Sprint 17 — Operator Cockpit IA Redesign

**Released:** 2026-06-28

**Product framing:** DemandOS now presents as an *inventory decision cockpit for forecast-driven reorder planning* — not a generic forecasting platform.

**Navigation:**
- Sidebar restructured into three semantic sections: **Operate** / **Trust** / **Setup**
- New operator-facing labels: Cockpit, Risk Board, Reorder Queue, Forecast Trust, Data Quality, Pipeline Trace, Data Sources
- ML Insights accessible via Forecast Trust cross-link; Monitoring via Data Quality

**New components:**
- `SituationBanner` — hero card with at-risk SKU count, exposure, and CTAs
- `DemoScenarioCard` — dataset context card
- `TrustBadge` — semantic trust badges (Strong/Directional/Weak/Synthetic demo/No external actions)
- `TechnicalTrace` — pipeline provenance strip

**Changes (no backend changes):**
- Cockpit: decision-oriented layout with SituationBanner + metric strip + risk/reorder panels + trend chart + pipeline trace
- Risk Board: triage framing, clearer safety note
- Reorder Queue: decision queue framing, internal-only safety copy
- Forecast Trust: trust-label header, clearer "can I trust this?" orientation
- Data Quality: completeness framing
- Pipeline Trace: technical-review note pointing casual users to Cockpit
- Scenarios: preset chips for demand/lead-time/inventory changes
- Data Sources: honest framing of disabled connector stubs
- Screenshots README updated with Sprint 17 pages (pending post-deploy capture)

**Safety:** No hardcoded KPIs, no new external actions, no new backend routes.
