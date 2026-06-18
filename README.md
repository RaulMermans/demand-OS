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
| 6 | Stockout risk engine (days-until-stockout, risk tiers, inventory coverage) | 🔜 Next |
| 7 | Reorder recommendations + model monitoring | 🔜 |
| 7+ | Real connectors (Shopify, CSV, WooCommerce) | 🔜 |

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

## CI

GitHub Actions runs on every push and PR:
- **backend**: Python 3.11, pytest, verify.sh
- **frontend**: Node LTS, `npm run build`
- **repo-hygiene**: no .env, no artifacts, no secrets committed

Local CI-equivalent:
```bash
cd apps/api && pytest && cd ../.. && bash scripts/verify.sh
cd apps/web && npm install && npm run build
```

---

## Connector Roadmap

| Connector | Status |
|-----------|--------|
| MockCommerceConnector | Stub (Sprint 1: full implementation) |
| CsvCommerceConnector | Stub (Sprint 2) |
| ShopifyConnector | Stub (Sprint 3) |
| WooCommerceConnector | Planned (Sprint 4) |
| BigCommerceConnector | Planned (Sprint 5) |
| ERPConnector | Future |

---

## References

Architecture and algorithm inspiration:
- [Nixtla/mlforecast](https://github.com/Nixtla/mlforecast) — global ML forecasting patterns
- [M5 Competition methods](https://github.com/Mcompetitions/M5-methods) — retail forecasting discipline
- [ecom_sales_data_generator](https://github.com/G-Schumacher44/ecom_sales_data_generator) — synthetic data patterns
- [inventory-optimization](https://github.com/virbahu/inventory-optimization) — EOQ, safety stock, ROP
- [unit8co/darts](https://github.com/unit8co/darts) — optional deep learning comparison

See [docs/reference_repositories.md](docs/reference_repositories.md) for details.
