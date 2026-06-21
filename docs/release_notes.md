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
- [ ] Refreshed deployment validated
- [ ] Updated automated screenshots captured
- [ ] Manual deployment/Neon/CI screenshots captured and redacted
- [ ] Maintainer selects a repository license if reuse is intended
