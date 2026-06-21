# DemandOS

**Demand forecasting and inventory risk platform.**

DemandOS ingests raw operational commerce records and computes demand forecasts,
stockout risk scores, and reorder recommendations — entirely from raw data.

---

## What is DemandOS?

DemandOS answers three questions for e-commerce and omnichannel retailers:

1. **How much will I sell?** — 28-day demand forecasts per SKU per store
2. **What will run out?** — Stockout risk scores with days-until-stockout
3. **What should I order?** — Reorder recommendations using EOQ + safety stock

---

## Raw-Data-Only Principle

> DemandOS never accepts precomputed ML features, forecasts, risk scores,
> or reorder recommendations as input.

The system ingests raw operational records:
- Orders, inventory snapshots, products, stores, suppliers, promotions, purchase orders

All derived values are computed internally:
- Feature engineering → forecasting → stockout risk → reorder recommendations

This makes the pipeline auditable, testable, and connector-agnostic.

---

## Architecture

```
Connector → Ingestion → Validation → Aggregation → Features → Forecasting → Risk → Recommendations
               ↓              ↓             ↓            ↓           ↓          ↓          ↓
           raw_* tables   validation     sales_daily  feature_    forecasts  stockout_  reorder_
                          errors         inv_daily    matrix                 risks      recs
                                                                  FastAPI ← ← ← ← ← ← ← ↑
                                                                  Next.js Dashboard
```

See [docs/architecture.md](docs/architecture.md) for full diagram.

---

## Sprint Status

| Sprint | Goal | Status |
|--------|------|--------|
| 0 | Scaffold | ✅ Done |
| 1 | Mock data generator (50 SKUs × 5 stores × 2yr) | ✅ Done |
| 2 | Aggregation pipeline (canonical daily tables) | ✅ Done |
| 3 | Feature engineering (leakage-safe feature_matrix) | ✅ Done |
| 4 | Baseline forecasting + backtesting (seasonal naive, moving average) | ✅ Done |
| 5 | ML forecasting (HistGradientBoosting global model) + model registry + CI | ✅ Done |
| 6 | Stockout risk engine (days-until-stockout, risk tiers, inventory coverage, lost sales) | ✅ Done |
| 7 | Reorder recommendation engine (ROP, EOQ, approval flow) | ✅ Done |
| 8 | Backend API hardening + dashboard data contracts | ✅ Done |
| 9 | Dashboard UX + safe pipeline controls + API key guard | ✅ Done |
| 10 | Demo orchestration + product drilldown + Vercel deployment | ✅ Done |
| 10B | Single Vercel project adapter (frontend + backend same project) | ✅ Done |
| 10C | Postgres FK insert order fix for Neon demo reset | ✅ Done |
| 11 | Production smoke validation + observability + case study prep | ✅ Done |
| 12 | Final screenshots, portfolio case study, MVP closeout | 🔜 Next |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional, for Postgres)

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd apps/web
npm install
# Create .env.local with: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Dashboard: http://localhost:3000

### Database (Postgres via Docker)

```bash
docker-compose up -d db
```

---

## Run Tests

```bash
cd apps/api
pytest
```

## Verify Everything

```bash
bash scripts/verify.sh
```

## Train the ML Model

```bash
# Seed data + run pipeline first
curl -X POST http://localhost:8000/api/demo/reset
curl -X POST http://localhost:8000/api/aggregation/run -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:8000/api/features/build -H 'Content-Type: application/json' -d '{}'

# Then train
python scripts/train_model.py --algorithm hist_gradient_boosting --horizon-days 28 --backtest-days 56

# Or via API
curl -X POST http://localhost:8000/api/models/train \
  -H 'Content-Type: application/json' \
  -d '{"algorithm": "hist_gradient_boosting", "horizon_days": 28, "backtest_days": 56}'
```

## Run Stockout Risk (Sprint 6)

```bash
# Full pipeline + risk scoring
curl -X POST http://localhost:8000/api/demo/reset
curl -X POST http://localhost:8000/api/aggregation/run -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:8000/api/features/build -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:8000/api/forecasts/baseline/run -H 'Content-Type: application/json' -d '{"model_type":"seasonal_naive"}'

# Generate forward-looking forecast rows (preferred for risk scoring)
curl -X POST http://localhost:8000/api/forecasts/planning/run \
  -H 'Content-Type: application/json' \
  -d '{"model_type": "seasonal_naive", "horizon_days": 28}'

# Run risk engine
curl -X POST http://localhost:8000/api/risks/run \
  -H 'Content-Type: application/json' \
  -d '{"horizon_days": 28, "mode": "forward_planning"}'

# View results
curl http://localhost:8000/api/risks/latest
curl http://localhost:8000/api/risks?risk_tier=critical

# Or via scripts
python scripts/run_planning_forecast.py --model seasonal_naive --horizon-days 28
python scripts/run_stockout_risk.py --horizon-days 28
```

## Vercel Deployment (Single Project)

Deploy the entire prototype as one Vercel project:

1. Import this repo in Vercel. Set **Root Directory** to `.` (repo root).
2. Add Neon Postgres via **Storage → Connect Store → Neon**.
3. Set environment variables in Vercel panel:
   ```
   DEMANDOS_API_KEY      = <strong-random-string>
   DEMANDOS_RUNTIME_MODE = vercel
   DEMANDOS_DEMO_SCALE   = small
   ```
   Leave `NEXT_PUBLIC_API_BASE_URL` **unset** (same-origin mode).
4. Deploy. Run migrations: `DATABASE_URL=<neon-url> alembic upgrade head`
5. Check readiness: `GET https://<domain>/api/readiness`

See [docs/deployment.md](docs/deployment.md) for full instructions and serverless limitations.

## Production Smoke Validation

```bash
# Read-only check against deployed app (no data mutation)
python scripts/smoke_production.py --base-url https://demand-os-three.vercel.app

# Full check including pipeline run (requires API key)
python scripts/smoke_production.py \
  --base-url https://demand-os-three.vercel.app \
  --api-key "$DEMANDOS_API_KEY" \
  --run-pipeline
```

Checks 15 conditions: readiness, all dashboard endpoints, runtime mode, demo scale,
core counts, recommendations, and no secrets leaked in any response.

## CI

GitHub Actions runs on every push and PR:
- **backend**: Python 3.11, pytest, verify.sh
- **frontend**: Node LTS, `npm run build`
- **repo-hygiene**: no .env, no artifacts, no secrets committed

Local CI-equivalent:
```bash
cd apps/api && python3 -m pytest && cd ../.. && bash scripts/verify.sh
cd apps/web && npm ci && npm run build
```

---

## Connector Roadmap

| Connector | Status |
|-----------|--------|
| MockCommerceConnector | ✅ Implemented (Sprint 1) |
| CsvCommerceConnector | Stub — Sprint 12+ |
| ShopifyConnector | Stub — Sprint 12+ |
| WooCommerceConnector | Planned |
| ERPConnector | Planned |

---

## References

Architecture and algorithm inspiration:
- [Nixtla/mlforecast](https://github.com/Nixtla/mlforecast) — global ML forecasting patterns
- [M5 Competition methods](https://github.com/Mcompetitions/M5-methods) — retail forecasting discipline
- [ecom_sales_data_generator](https://github.com/G-Schumacher44/ecom_sales_data_generator) — synthetic data patterns
- [inventory-optimization](https://github.com/virbahu/inventory-optimization) — EOQ, safety stock, ROP
- [unit8co/darts](https://github.com/unit8co/darts) — optional deep learning comparison

See [docs/reference_repositories.md](docs/reference_repositories.md) for details.
