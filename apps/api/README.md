# DemandOS API

FastAPI backend for the DemandOS demand forecasting and inventory risk platform.

## Local Setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Test

```bash
pytest
```

## Database Migrations (Alembic)

DemandOS uses Alembic for production-grade schema management.

```bash
# Apply all pending migrations (create tables)
alembic upgrade head

# Generate a new migration after changing models.py
alembic revision --autogenerate -m "describe the change"

# Downgrade one step
alembic downgrade -1
```

The default database URL is `sqlite:///./demandos_dev.db` (from `config.py`).
Override with the `DATABASE_URL` environment variable.

The initial migration (`alembic/versions/0001_initial_schema.py`) covers all
Sprint 0–7 tables. The app uses `create_all()` for development; Alembic is the
path to production Postgres.

## API Response Contracts (Sprint 8)

All major API responses use explicit Pydantic schemas defined in
`app/schemas/api.py`. No raw ORM objects are returned.

### Pagination

List endpoints accept `limit` and `offset` query parameters:

| Endpoint | Default limit | Max limit |
|----------|--------------|-----------|
| `/api/forecasts/runs` | 20 | 100 |
| `/api/forecasts/latest` | 50 | 500 |
| `/api/model-metrics` | 100 | 500 |
| `/api/risks/runs` | 20 | 100 |
| `/api/risks` | 100 | 1000 |
| `/api/recommendations/runs` | 20 (internal) | — |
| `/api/recommendations` | 100 | — |

Invalid `limit` values return HTTP 422 with a clear error.

### No-data States

Endpoints return honest statuses when no pipeline run exists:
- `status: "no_data"` — overview with no ingested data
- `status: "no_forecast"` — no completed forecast run
- `status: "no_risk_run"` — no completed risk run
- `status: "no_data"` — no completed recommendation run

### Dashboard Endpoints

```
GET /api/dashboard/overview              — full pipeline status + counts
GET /api/dashboard/forecast-summary     — latest forecast run + metrics
GET /api/dashboard/risk-summary         — risk tier counts + lost sales
GET /api/dashboard/recommendation-summary — urgency counts + open recs
GET /api/dashboard/model-summary        — ML vs baseline comparison
GET /api/dashboard/data-health          — same as /api/data-health
```

These aggregate already-computed data. They introduce no new formulas.

## Architecture

```
connector → ingestion → validation → aggregation → features
→ forecasting (baseline + ML) → stockout risk → recommendations
→ dashboard API
```

Each service reads from the DB and writes to the DB.
No stateful in-memory chains. No automatic purchase orders.

## Sprint Status

| Sprint | Goal | Status |
|--------|------|--------|
| 0 | Scaffold | ✅ Done |
| 1 | Mock data generator | ✅ Done |
| 2 | Aggregation pipeline | ✅ Done |
| 3 | Feature engineering | ✅ Done |
| 4 | Baseline forecasting | ✅ Done |
| 5 | ML model + registry + CI | ✅ Done |
| 6 | Stockout risk engine | ✅ Done |
| 7 | Reorder recommendations | ✅ Done |
| 8 | API contracts + Alembic | ✅ Done |
| 9 | Dashboard UX + pipeline controls | 🔜 Next |
