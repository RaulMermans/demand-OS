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

## Architecture

```
connector → ingestion → validation → aggregation → features → forecasting → stockout → recommendations
```

All services read from the DB, not from connectors directly (except IngestionService).

## Sprint Status

| Sprint | Goal | Status |
|--------|------|--------|
| 0 | Scaffold | ✅ Done |
| 1 | Mock data generator | 🔜 Next |
| 2 | Aggregation pipeline | 🔜 |
| 3 | Feature engineering | 🔜 |
| 4 | LightGBM forecasting | 🔜 |
| 5 | Stockout + reorder | 🔜 |
| 6 | Model evaluation | 🔜 |
