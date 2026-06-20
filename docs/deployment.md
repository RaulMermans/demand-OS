# DemandOS — Deployment Guide

This document covers deploying the DemandOS frontend to Vercel and preparing the backend
for future external service deployment.

---

## Architecture

```
┌──────────────────────────────────────────┐
│  Vercel (frontend)                        │
│  apps/web — Next.js dashboard             │
│  NEXT_PUBLIC_API_BASE_URL → backend URL   │
└──────────────────────────────┬───────────┘
                               │ HTTP/HTTPS
┌──────────────────────────────▼───────────┐
│  Backend (Render / Railway / Fly.io)      │
│  apps/api — FastAPI + ML pipeline         │
│  DATABASE_URL → Postgres                  │
│  DEMANDOS_API_KEY → write guard           │
└──────────────────────────────┬───────────┘
                               │
┌──────────────────────────────▼───────────┐
│  Managed Postgres (e.g., Supabase/Neon)  │
└──────────────────────────────────────────┘
```

---

## Vercel Frontend Deployment

### GUI Setup

1. Go to [vercel.com](https://vercel.com) and import the GitHub repository.
2. In **Root Directory**, select `apps/web`.
3. Framework preset: **Next.js** (auto-detected).
4. Build Command: `npm run build` (override if needed; matches `vercel.json`).
5. Install Command: `npm ci`.
6. Output Directory: `.next` (default for Next.js).
7. Add environment variable:
   ```
   NEXT_PUBLIC_API_BASE_URL = https://<your-backend-service-domain>
   ```
8. Click **Deploy**.
9. Verify the dashboard loads and `/api/overview` returns a response from the backend.

### CLI Setup

```bash
cd apps/web
npm install -g vercel   # if not installed

# Deploy to preview
vercel

# Deploy to production
vercel --prod
```

The CLI will prompt for team, project name, and root directory (`apps/web`).

### Vercel Environment Variables

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | `https://api.demandos.example.com` | Backend API URL without trailing slash |

**Never set `DEMANDOS_API_KEY` as a Vercel env var.** The API key is entered by the operator
in the `/pipeline` page UI and stored only in `sessionStorage`.

### Local Vercel-equivalent Build Check

Run these before deploying to catch TypeScript and build errors locally:

```bash
cd apps/web
npm ci
npm run typecheck --if-present
npm run build
```

---

## Backend Deployment (Future — Sprint 11+)

The FastAPI backend is a Python ML service and should NOT be deployed to Vercel.
Recommended targets:

- [Render](https://render.com) — free tier available, supports Python web services
- [Railway](https://railway.app) — free tier, automatic deployments from GitHub
- [Fly.io](https://fly.io) — more control, Docker-based

### Required Environment Variables (Backend)

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes (prod) | `sqlite:///./demandos_dev.db` | PostgreSQL URL in production |
| `DEMANDOS_API_KEY` | Optional | _(empty — guard disabled)_ | Secret key for write endpoint protection |
| `APP_NAME` | No | `DemandOS API` | Application name |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | List of allowed frontend origins |

### Alembic Database Migrations

After deploying the backend with a new Postgres database:

```bash
cd apps/api
alembic upgrade head
```

This applies all schema migrations in order.

To check current migration state:
```bash
alembic current
```

### Model Artifacts

The ML training service saves model artifacts to `models/forecasting/{version_id}.joblib`.
In production, this directory should be on persistent storage (e.g., a mounted volume).
Currently, model artifacts are local to the process — restarting the process without
persistent storage will lose existing artifacts (models can be retrained via `POST /api/models/train`).

### Backend Health Check

```bash
curl https://<backend-url>/health
# Expected: {"status": "ok", "version": "...", "environment": "..."}
```

---

## Local Development

### Backend

```bash
cd apps/api
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/web
npm ci
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
```

Dashboard available at http://localhost:3000

---

## Verification

Run the full verification suite before any deployment:

```bash
bash scripts/verify.sh
```

This checks all required files, runs pytest, verifies the frontend structure,
and validates that no forbidden derived fields appear in raw schemas.
