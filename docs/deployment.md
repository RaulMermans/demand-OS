# DemandOS — Deployment Guide

This document covers two deployment modes:
1. **Single Vercel Project** (recommended for prototype/demo) — frontend + backend in one Vercel project
2. **Separate Services** (recommended for production) — Next.js on Vercel, FastAPI on Render/Railway/Fly.io

---

## Option A — Single Vercel Project (prototype/demo)

This is the recommended mode for internal demos. Frontend and backend are served from the same
Vercel project domain, so `NEXT_PUBLIC_API_BASE_URL` can be left blank.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Vercel Project (deployed from repo root ./)             │
│                                                          │
│  / → apps/web (Next.js — @vercel/next)                  │
│  /api/* → api/index.py (FastAPI — @vercel/python)       │
│                                                          │
│  Required env vars:                                      │
│    DATABASE_URL          ← Neon Postgres (Marketplace)   │
│    DEMANDOS_API_KEY      ← write-endpoint guard          │
│    DEMANDOS_RUNTIME_MODE = vercel                        │
│    DEMANDOS_DEMO_SCALE   = small                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  Neon Postgres (via Vercel Marketplace integration)      │
│  DATABASE_URL injected automatically                     │
└─────────────────────────────────────────────────────────┘
```

### Vercel Project Setup

1. Go to [vercel.com](https://vercel.com) and import the GitHub repository.
2. **Root Directory**: leave as `.` (repo root) — **not** `apps/web`.
3. Framework preset: **Other** (not Next.js — the `vercel.json` handles routing).
4. Vercel will detect `vercel.json` automatically and apply the build config.

### Install Neon from Vercel Marketplace

1. In your Vercel project → **Storage** → **Connect Store** → **Neon**.
2. Create a new database or link an existing one.
3. Vercel injects `DATABASE_URL` automatically into all deployments and preview environments.

### Required Vercel Environment Variables

Set these in **Vercel Project → Settings → Environment Variables**:

| Variable | Value | Scope |
|----------|-------|-------|
| `DEMANDOS_API_KEY` | A strong random string | Production + Preview |
| `DEMANDOS_RUNTIME_MODE` | `vercel` | Production + Preview |
| `DEMANDOS_DEMO_SCALE` | `small` | Production + Preview |
| `DATABASE_URL` | _(injected by Neon integration — do not set manually)_ | All |

`NEXT_PUBLIC_API_BASE_URL` should be **left unset** for same-origin API calls.

### Database Migrations

Migrations must be run once after the first deployment (and after each schema change):

```bash
# Option 1 — from local machine using the Neon connection string
DATABASE_URL="<neon-connection-string>" cd apps/api && alembic upgrade head

# Option 2 — via Vercel Build Command (add to vercel.json if desired)
# "buildCommand": "cd apps/web && npm ci && npm run build && cd ../../apps/api && alembic upgrade head"
```

### Serverless Limitations

Running on Vercel Serverless means:
- **No durable local filesystem** — model artifacts written to `/tmp` are lost between invocations.
  The `ModelVersion` row in Postgres records `artifact_path = "vercel_ephemeral"` to document this.
  Metrics and forecast results are fully persisted in Postgres.
- **No background jobs** — the demo pipeline runs synchronously within a single request.
  With `DEMANDOS_DEMO_SCALE=small` (10 products, 2 stores, 180 days) this fits within
  Vercel's 60-second serverless function timeout.
- **Cold starts** — the first request after a period of inactivity may be slow
  while dependencies are loaded into the Lambda container.
- **No external purchase orders, emails, or Slack alerts** — these are disabled by design.

### Readiness Check

```bash
curl https://<your-vercel-domain>/api/readiness
# Expected when configured:
# {"ready": true, "status": "ok", "runtime_mode": "vercel", "demo_scale": "small", "reason": null}
#
# Expected when DATABASE_URL is missing/SQLite:
# {"ready": false, "status": "not_ready", "runtime_mode": "vercel", ...}
```

### Migrating to a Dedicated Backend (Sprint 11+)

To move from single-project Vercel to a dedicated backend:
1. Deploy `apps/api` to Render / Railway / Fly.io.
2. Set `NEXT_PUBLIC_API_BASE_URL=https://<backend-domain>` in Vercel frontend.
3. Set `DEMANDOS_RUNTIME_MODE=local` on the backend host.
4. Remove `DEMANDOS_RUNTIME_MODE` and `DEMANDOS_DEMO_SCALE` from Vercel backend env vars
   (they only apply to the Python function).
5. Point `api/index.py` imports to the remote URL, or remove the Python function.

---

## Option B — Separate Services (production)

### Architecture

```
┌──────────────────────────────────────────┐
│  Vercel (frontend — root dir: apps/web)   │
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
│  Managed Postgres (e.g., Neon/Supabase)  │
└──────────────────────────────────────────┘
```

### Vercel Frontend (apps/web)

1. Import the GitHub repository in Vercel.
2. **Root Directory**: `apps/web`.
3. Framework preset: **Next.js** (auto-detected).
4. Build Command: `npm run build`.
5. Install Command: `npm ci`.
6. Add environment variable:
   ```
   NEXT_PUBLIC_API_BASE_URL = https://<your-backend-service-domain>
   ```

### Backend Required Environment Variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `DATABASE_URL` | Yes (prod) | `sqlite:///./demandos_dev.db` | PostgreSQL URL in production |
| `DEMANDOS_API_KEY` | Optional | _(empty — guard disabled)_ | Secret key for write endpoint protection |
| `APP_NAME` | No | `DemandOS API` | Application name |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `CORS_ORIGINS` | No | `["http://localhost:3000"]` | List of allowed frontend origins |

### Alembic Database Migrations

```bash
cd apps/api
alembic upgrade head
```

### Model Artifacts

The ML training service saves artifacts to `models/forecasting/{version_id}.joblib`.
In production, this directory should be on persistent storage (mounted volume or object store).

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

Dashboard available at http://localhost:3000.

---

## Verification

Run the full verification suite before any deployment:

```bash
bash scripts/verify.sh
```

This checks all required files (including Vercel deployment adapter files), runs pytest,
verifies the frontend structure, and validates that no forbidden derived fields appear
in raw schemas.
