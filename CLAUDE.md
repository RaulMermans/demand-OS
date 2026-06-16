# CLAUDE.md — DemandOS Project Memory

This file is the authoritative instruction set for AI coding agents working in this repository.
Read this before making any change.

---

## Project Mission

DemandOS is a demand forecasting and inventory risk platform.
It ingests raw operational commerce records and computes all derived insights internally.
The product must behave like a real ML system even with synthetic/mock data.

---

## Non-Negotiable Rule: Raw Data Only

**DemandOS must never require precomputed ML features, forecasts, stockout scores,
or reorder recommendations as input.**

Connectors return raw operational records:
- Orders, inventory snapshots, products, stores, suppliers, promotions, purchase orders

The pipeline computes everything else:
- Lag features, rolling windows, calendar features
- Demand forecasts and prediction intervals
- Stockout probability and days-until-stockout
- Safety stock, reorder point, EOQ, reorder recommendations

**If you are ever tempted to put a derived field into a connector or raw schema,
stop and put it in the appropriate downstream service instead.**

The test `tests/test_raw_data_rule.py` enforces this automatically.

---

## Architecture: Deterministic ML Workflow

DemandOS is NOT an agentic system. It is a deterministic, code-defined pipeline:

```
Connector → IngestionService → ValidationService → AggregationService
→ FeatureService → ForecastingService → StockoutService → RecommendationService
```

Each service reads from the database, writes to the database.
No stateful in-memory chains between services.
AI/LLM is used to WRITE this pipeline (you), not to run inside it at inference time.

See `docs/decisions/0001-deterministic-ml-workflow.md`.

---

## Folder Responsibilities

| Folder | What goes here |
|--------|---------------|
| `apps/api/app/connectors/` | Data source connectors; return raw schemas only |
| `apps/api/app/schemas/raw.py` | Raw operational record Pydantic schemas; NO derived fields |
| `apps/api/app/schemas/derived.py` | Computed output schemas; never input to connectors |
| `apps/api/app/services/` | Pipeline logic; each service is a single responsibility |
| `apps/api/app/db/models.py` | SQLAlchemy ORM; all layers defined here |
| `apps/api/app/api/` | FastAPI route handlers; thin — delegate to services |
| `apps/api/tests/` | Pytest tests; one file per concern |
| `apps/web/` | Next.js frontend; reads from API only |
| `docs/` | Architecture, sprint plans, ML plans; update when code changes |
| `scripts/` | CLI utilities; never modify production DB without flags |
| `data/` | Raw files and uploads; never commit real customer data |

---

## Verification Behavior

After any change, run:

```bash
cd apps/api && pytest
```

After any schema change, also run:

```bash
cd apps/api && pytest tests/test_raw_data_rule.py -v
```

Do not mark a task complete until tests pass.

---

## Data Safety Rules

1. Never commit `.env` files (they are gitignored).
2. Never store credentials in the database or logs.
3. Never commit real customer data to `data/`.
4. The `raw_payload` column stores original JSON for debugging only; do not log its contents.
5. No automatic purchase orders — recommendations are human-approved only.

---

## No Hardcoded Dashboard Values

The frontend must never display hardcoded business metrics pretending to be computed.

**Acceptable:**
```
Forecast Explorer — scaffold ready. No model has been trained yet.
```

**Never acceptable:**
```
Forecast accuracy: 94%
Revenue at risk: €120,000
```

---

## Testing Standards

- Every new service gets at least one test.
- Raw schema changes must pass `test_raw_data_rule.py`.
- Connector changes must pass `test_connector_contract.py`.
- API changes must include a basic response shape test in `test_health.py` or a new test file.

---

## Documentation Standards

- Update `docs/sprint_plan.md` when starting or completing a sprint.
- Update `docs/architecture.md` if the pipeline sequence changes.
- Update `docs/data_contract.md` if raw schemas change.
- Update `docs/ml_plan.md` if forecasting approach changes.
- Add a new `docs/decisions/NNNN-*.md` for any significant architectural decision.

---

## What NOT to Do

- Do not add real Shopify/WooCommerce/ERP API calls in stubs.
- Do not add mock ML feature columns (lag_7d, rolling_mean_*) to raw schemas.
- Do not implement full ML models ahead of their sprint.
- Do not introduce uncontrolled autonomy (agents calling agents in a loop).
- Do not add external side effects (emails, Slack messages, purchase orders) without
  explicit approval gates and feature flags.
- Do not create fake computed metrics in the dashboard.
