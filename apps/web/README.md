# DemandOS Web

Next.js 14 frontend for the DemandOS demand forecasting platform.

## Local Setup

```bash
cd apps/web
npm install
cp ../../.env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run

```bash
npm run dev
# Open http://localhost:3000
```

## Build

```bash
npm run build
```

## Routes

| Route | Sprint | Description |
|-------|--------|-------------|
| `/` | 0 | Home / status dashboard |
| `/overview` | 2 | Pipeline overview and record counts |
| `/forecasts` | 4 | 28-day demand forecast explorer |
| `/risks` | 5 | Stockout risk heatmap |
| `/model-performance` | 6 | RMSE / SMAPE / bias metrics |
| `/data-health` | 1 | Validation report and ingestion history |
