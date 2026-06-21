"""
Sprint 10B — Tests for single Vercel project deployment adapter.

Covers:
  J1.  root vercel.json exists
  J2.  api/index.py exists
  J3.  api.index.app imports the FastAPI app
  J4.  frontend API client supports same-origin /api when base URL is blank
  J5.  vercel runtime mode does not require durable local model artifact storage
  J6.  small demo config is available
  J7.  readiness reports not_ready when vercel mode has no DATABASE_URL
  J8.  API key guard still works (smoke test)
  J9.  (covered by existing suite — this file focuses on J1-J8 and J10)
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


# ---------------------------------------------------------------------------
# J1 — root vercel.json exists
# ---------------------------------------------------------------------------

def test_root_vercel_json_exists():
    path = os.path.join(ROOT, "vercel.json")
    assert os.path.isfile(path), "vercel.json must exist at the repo root for single Vercel project mode"


def test_root_vercel_json_has_api_route():
    import json
    path = os.path.join(ROOT, "vercel.json")
    with open(path) as f:
        config = json.load(f)
    # Must define a route for /api/* pointing to api/index.py
    routes = config.get("routes", [])
    api_route = next((r for r in routes if r.get("src", "").startswith("/api")), None)
    assert api_route is not None, "vercel.json must route /api/* to the Python function"
    assert "index.py" in api_route.get("dest", ""), "vercel.json /api route must point to api/index.py"


def test_root_vercel_json_builds_nextjs():
    import json
    path = os.path.join(ROOT, "vercel.json")
    with open(path) as f:
        config = json.load(f)
    builds = config.get("builds", [])
    next_build = next((b for b in builds if "next" in b.get("use", "").lower()), None)
    assert next_build is not None, "vercel.json must include a @vercel/next build for the frontend"


# ---------------------------------------------------------------------------
# J4 — frontend API client supports same-origin /api when base URL is blank
# ---------------------------------------------------------------------------

def test_frontend_api_client_same_origin_when_base_url_blank():
    """lib/api.ts must use same-origin relative paths when NEXT_PUBLIC_API_BASE_URL is blank.

    Structural check: reads the TypeScript source and verifies that the BASE variable
    defaults to empty string (not "http://localhost:8000") when the env var is absent.
    """
    api_ts = os.path.join(ROOT, "apps", "web", "lib", "api.ts")
    assert os.path.isfile(api_ts), "apps/web/lib/api.ts must exist"
    with open(api_ts) as f:
        source = f.read()

    # The key pattern: env var present → use it; absent → empty string (same-origin)
    assert "NEXT_PUBLIC_API_BASE_URL" in source, "api.ts must reference NEXT_PUBLIC_API_BASE_URL"
    # Must NOT fall back to "http://localhost:8000" as the default when env var is absent
    # (that was the old pattern — the ?? "http://localhost:8000" fallback)
    assert '?? "http://localhost:8000"' not in source, (
        "api.ts must NOT fall back to localhost:8000 — blank BASE means same-origin /api calls"
    )
    # Must produce an empty BASE when env var is not set
    # Accept either: `? env.replace(...) : ""` or similar patterns
    assert ': ""' in source or "= \"\"" in source, (
        "api.ts must produce an empty string BASE when NEXT_PUBLIC_API_BASE_URL is unset"
    )


# ---------------------------------------------------------------------------
# J2 — api/index.py exists
# ---------------------------------------------------------------------------

def test_api_index_py_exists():
    path = os.path.join(ROOT, "api", "index.py")
    assert os.path.isfile(path), "api/index.py must exist as the Vercel Python function entry-point"


# ---------------------------------------------------------------------------
# J3 — api/index.py exposes the FastAPI app (structural check)
# ---------------------------------------------------------------------------

def test_api_index_py_exposes_app():
    """api/index.py must expose `app` and import it from app.main."""
    path = os.path.join(ROOT, "api", "index.py")
    with open(path) as f:
        source = f.read()
    assert "from app.main import app" in source, (
        "api/index.py must import `app` from app.main — do not duplicate the FastAPI app"
    )
    assert '__all__' in source or 'app' in source, (
        "api/index.py must expose `app` for Vercel ASGI discovery"
    )


def test_api_index_app_is_fastapi():
    """Import api/index.py via sys.path and confirm it exposes the FastAPI ASGI app."""
    from fastapi import FastAPI

    api_dir = os.path.join(ROOT, "api")
    apps_api_dir = os.path.join(ROOT, "apps", "api")

    original_path = sys.path.copy()
    # Prepend both so the adapter and the source are importable
    for p in [apps_api_dir, api_dir]:
        if p not in sys.path:
            sys.path.insert(0, p)

    # Remove any cached version so the import executes fresh
    for mod_name in list(sys.modules):
        if mod_name == "index":
            del sys.modules[mod_name]

    try:
        import index as api_index  # resolves to api/index.py
        assert hasattr(api_index, "app"), "api/index.py must expose an `app` object"
        assert isinstance(api_index.app, FastAPI), "api/index.app must be a FastAPI instance"
    finally:
        sys.path[:] = original_path
        # Clean up the dynamically imported module
        sys.modules.pop("index", None)


# ---------------------------------------------------------------------------
# J5 — vercel runtime mode does not require durable local model artifact storage
# ---------------------------------------------------------------------------

def test_vercel_mode_artifact_dir_uses_tmp(monkeypatch):
    """In vercel mode, TrainingService._default_artifact_dir() must use /tmp."""
    from app import config as cfg_module
    from app.config import Settings

    # _default_artifact_dir() does a local `from app.config import get_settings` call.
    # Patch the lru_cache'd function so it returns vercel settings.
    vercel_settings = Settings(demandos_runtime_mode="vercel", database_url="sqlite:///./test.db")
    monkeypatch.setattr(cfg_module, "get_settings", lambda: vercel_settings)

    from app.services.training_service import _default_artifact_dir
    artifact_dir = _default_artifact_dir()
    assert artifact_dir.startswith("/tmp"), (
        f"In vercel mode, artifact dir must be /tmp-based, got: {artifact_dir}"
    )


# ---------------------------------------------------------------------------
# J6 — small demo config is available
# ---------------------------------------------------------------------------

def test_small_demo_scale_config(monkeypatch):
    """DEMANDOS_DEMO_SCALE=small produces smaller seed parameters."""
    from app import config as cfg_module
    from app.config import Settings

    monkeypatch.setenv("DEMANDOS_DEMO_SCALE", "small")
    cfg_module.get_settings.cache_clear()
    try:
        # _scale_defaults() reads get_settings() at call time, so clearing cache suffices
        from app.api.demo import _scale_defaults
        defaults = _scale_defaults()
        assert defaults["product_count"] == 10
        assert defaults["store_count"] == 2
        assert defaults["history_days"] == 180
    finally:
        cfg_module.get_settings.cache_clear()
        monkeypatch.delenv("DEMANDOS_DEMO_SCALE", raising=False)


def test_full_demo_scale_config(monkeypatch):
    """DEMANDOS_DEMO_SCALE=full (default) produces full-size parameters."""
    from app import config as cfg_module

    monkeypatch.setenv("DEMANDOS_DEMO_SCALE", "full")
    cfg_module.get_settings.cache_clear()
    try:
        from app.api.demo import _scale_defaults
        defaults = _scale_defaults()
        assert defaults["product_count"] == 50
        assert defaults["store_count"] == 5
        assert defaults["history_days"] == 730
    finally:
        cfg_module.get_settings.cache_clear()
        monkeypatch.delenv("DEMANDOS_DEMO_SCALE", raising=False)


# ---------------------------------------------------------------------------
# J7 — readiness reports not_ready when vercel mode has no DATABASE_URL
# ---------------------------------------------------------------------------

def _make_vercel_settings(database_url: str = "sqlite:///./test.db"):
    """Create a Settings object that looks like a Vercel deployment with SQLite URL."""
    from app.config import Settings
    return Settings(
        demandos_runtime_mode="vercel",
        database_url=database_url,
        demandos_demo_scale="small",
    )


def _make_local_settings():
    """Create a Settings object for local mode."""
    from app.config import Settings
    return Settings(demandos_runtime_mode="local", database_url="sqlite:///./test.db")


def test_readiness_not_ready_in_vercel_without_postgres(override_db, monkeypatch):
    """Health readiness endpoint returns not_ready when vercel mode + SQLite URL."""
    vercel_settings = _make_vercel_settings()
    monkeypatch.setattr("app.api.health.get_settings", lambda: vercel_settings)

    from app.main import app
    client = TestClient(app)
    response = client.get("/api/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["ready"] is False
    assert data["runtime_mode"] == "vercel"


def test_readiness_ok_in_local_mode(override_db, monkeypatch):
    """Health readiness endpoint returns ok when runtime_mode=local."""
    local_settings = _make_local_settings()
    monkeypatch.setattr("app.api.health.get_settings", lambda: local_settings)

    from app.main import app
    client = TestClient(app)
    response = client.get("/api/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ready"] is True


def test_health_not_ready_in_vercel_without_postgres(override_db, monkeypatch):
    """GET /health returns not_ready status when vercel mode + SQLite."""
    vercel_settings = _make_vercel_settings()
    monkeypatch.setattr("app.api.health.get_settings", lambda: vercel_settings)

    from app.main import app
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"


# ---------------------------------------------------------------------------
# J8 — API key guard still works
# ---------------------------------------------------------------------------

def test_api_key_guard_still_blocks_without_key(override_db, monkeypatch):
    """POST /api/demo/reset returns 401 when API key is required but not sent.

    The auth guard returns 401 (not 403) when the key header is absent or wrong.
    This matches the existing test_api_key_guard.py::test_guard_blocks_missing_key.
    """
    from app.config import Settings, get_settings

    # Patch auth.get_settings to return a settings object with a real key configured
    keyed_settings = Settings(
        **{**get_settings().model_dump(), "demandos_api_key": "test-key-10b"}
    )
    monkeypatch.setattr("app.api.auth.get_settings", lambda: keyed_settings)

    from app.main import app
    client = TestClient(app)
    response = client.post("/api/demo/reset", json={})
    # Auth guard raises 401 when key is required but missing (matches auth.py behaviour)
    assert response.status_code == 401
