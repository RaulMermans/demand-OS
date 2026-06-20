# DemandOS Web

Next.js 14 frontend for the DemandOS demand forecasting and inventory risk platform.

## Local Setup

```bash
cd apps/web
npm install
# Create .env.local and set:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

## Run

```bash
npm run dev
# Open http://localhost:3000
```

## Build & Type Check

```bash
npm run build           # Production build (includes type check)
npm run type-check      # TypeScript only
```

## Routes (Sprint 8)

| Route | Description |
|-------|-------------|
| `/` | Home — pipeline status overview |
| `/overview` | Full pipeline metrics and run statuses |
| `/forecasts` | Demand forecast runs and model accuracy |
| `/risks` | Stockout risk scores ranked by tier |
| `/recommendations` | Reorder recommendations with status workflow |
| `/model-performance` | ML vs baseline comparison and model registry |
| `/data-health` | Record counts and validation checks for all layers |

All pages fetch from the backend via `lib/api.ts` using `NEXT_PUBLIC_API_BASE_URL`.
No page hardcodes business metrics or fake data.
All pages handle loading, error, and empty states.

## Frontend API Client

`lib/api.ts` — typed client functions for every backend endpoint.
`lib/types.ts` — TypeScript interfaces matching Pydantic response schemas.

## Reusable Components

| Component | Purpose |
|-----------|---------|
| `LoadingState` | Spinner for async page loads |
| `ErrorState` | Error with optional retry button |
| `EmptyState` | Empty state with title and message |
| `StatusBadge` | Color-coded badge for risk tier / pipeline status |
| `DataTable` | Generic typed data table |
| `MetricCard` | Single metric card |
| `AppShell` | Layout shell with nav sidebar |
| `PlaceholderPanel` | Scaffold placeholder (used before data is available) |
