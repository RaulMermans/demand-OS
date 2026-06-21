---
name: demandos-project-status
description: Current sprint status for DemandOS — latest sprint, test count, deployed state
metadata:
  type: project
---

Sprint 11 complete. 709 backend tests passing.

**Why:** Sprint 11 added production smoke validation, observability endpoints, readiness
polish, UI label update, case study docs, and QA checklist.

**How to apply:** Sprint 12 is next — final screenshots, case study finalization, MVP closeout.

## Completed Sprints
- Sprints 0–10C: scaffold → aggregation → features → forecasting → stockout → recs → dashboard → Vercel deployment
- Sprint 11: smoke script, observability, readiness/runtime endpoints, UI polish, docs

## Current State
- Deployed: https://demand-os-three.vercel.app
- Backend tests: 709 passing
- verify.sh: passing (exit 0)
- Runtime mode: vercel + Neon Postgres
- Demo scale: small (10 products, 2 stores, 180 days)

## New in Sprint 11
- `scripts/smoke_production.py` — 15-check production smoke test
- `GET /api/observability/runs-summary`
- `GET /api/observability/failure-summary`
- `GET /api/readiness` polished (api_key_guard_enabled, external_side_effects_enabled, checks)
- `GET /api/runtime/check`
- Sidebar label updated to "Deployed MVP · Demo Mode"
- Runtime status indicator in sidebar (fetches /api/readiness)
- ErrorState: distinguishes API key errors, backend unavailable, no data
- EmptyState: showPipelineLink prop
- docs/case_study.md, docs/demo_script.md, docs/case_study_assets.md, docs/final_qa_checklist.md
