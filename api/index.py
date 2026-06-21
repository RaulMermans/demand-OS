"""
Vercel Python Function adapter for DemandOS FastAPI backend.

This file is the single entry-point for all /api/* routes when deployed
to Vercel. Vercel's Python runtime discovers the `app` ASGI object here
and routes traffic to it.

Import path setup: apps/api is added to sys.path so the existing FastAPI
application can be imported without duplication. The application itself
lives in apps/api/app/main.py — nothing is duplicated here.

Vercel env vars required:
  DATABASE_URL          — Neon Postgres connection string
  DEMANDOS_API_KEY      — write-endpoint guard key
  DEMANDOS_RUNTIME_MODE — must be "vercel"
  DEMANDOS_DEMO_SCALE   — "small" recommended for Vercel (avoids timeouts)
"""

import os
import sys

# Make apps/api importable as "app.*" — Vercel runs from the repo root,
# so we resolve the path relative to this file.
_HERE = os.path.dirname(os.path.abspath(__file__))
_API_SRC = os.path.normpath(os.path.join(_HERE, "..", "apps", "api"))
if _API_SRC not in sys.path:
    sys.path.insert(0, _API_SRC)

from app.main import app  # noqa: E402 — intentional: must follow sys.path setup

__all__ = ["app"]
