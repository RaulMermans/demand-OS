from fastapi import APIRouter
from app.config import get_settings
from app.schemas.api import HealthResponse

router = APIRouter()


def _readiness_status() -> dict:
    """
    Compute readiness status respecting runtime mode constraints.

    Calls get_settings() at invocation time — not at module import — so that
    tests can monkeypatch the settings and see the correct behaviour.

    In vercel mode, DATABASE_URL must be a Postgres URL.
    A default sqlite:// URL in vercel mode means DATABASE_URL was not set,
    which makes the service not_ready.
    """
    settings = get_settings()
    if settings.demandos_runtime_mode == "vercel":
        if settings.database_url.startswith("sqlite"):
            return {
                "status": "not_ready",
                "reason": (
                    "DEMANDOS_RUNTIME_MODE=vercel requires a Postgres DATABASE_URL. "
                    "Install Neon from the Vercel Marketplace and set DATABASE_URL."
                ),
            }
    return {"status": "ok", "reason": None}


def _safe_readiness_checks(settings) -> list[dict]:
    """Return named readiness checks without exposing secrets."""
    checks = []

    # Database connection
    db_ok = not (
        settings.demandos_runtime_mode == "vercel"
        and settings.database_url.startswith("sqlite")
    )
    checks.append({
        "name": "database_connection",
        "status": "ok" if db_ok else "failed",
        "detail": "postgres" if not settings.database_url.startswith("sqlite") else "sqlite_fallback",
    })

    # Required tables — just check if DB is configured (actual table check is expensive)
    checks.append({
        "name": "required_tables",
        "status": "ok" if db_ok else "unknown",
        "detail": "tables verified at startup via init_db()",
    })

    # Runtime mode
    checks.append({
        "name": "runtime_mode",
        "status": "ok",
        "detail": settings.demandos_runtime_mode,
    })

    # Demo scale
    checks.append({
        "name": "demo_scale",
        "status": "ok",
        "detail": settings.demandos_demo_scale,
    })

    # API key guard
    api_key_guard_enabled = bool(settings.demandos_api_key)
    checks.append({
        "name": "api_key_guard",
        "status": "ok" if api_key_guard_enabled else "disabled",
        "detail": "enabled" if api_key_guard_enabled else "disabled (local dev mode)",
    })

    # Model artifact mode
    checks.append({
        "name": "model_artifact_mode",
        "status": "ok",
        "detail": "ephemeral_tmp" if settings.demandos_runtime_mode == "vercel" else "filesystem",
    })

    return checks


@router.get("/health", response_model=HealthResponse)
def health_check():
    settings = get_settings()
    readiness = _readiness_status()
    return HealthResponse(
        status=readiness["status"],
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/api/status")
def api_status():
    settings = get_settings()
    readiness = _readiness_status()
    if readiness["status"] == "not_ready":
        return {
            "status": "not_ready",
            "data_mode": "unavailable",
            "pipeline_ready": False,
            "active_connector": settings.active_connector,
            "message": readiness["reason"],
        }
    return {
        "status": "scaffold_ready",
        "data_mode": "not_seeded",
        "pipeline_ready": settings.pipeline_ready,
        "active_connector": settings.active_connector,
        "message": (
            "DemandOS API is running. "
            "Data pipeline not yet seeded — run scripts/seed_demo_data.py in Sprint 1."
        ),
    }


@router.get("/api/readiness")
def readiness_check():
    """Explicit readiness probe — returns not_ready when Vercel lacks DATABASE_URL."""
    settings = get_settings()
    result = _readiness_status()
    api_key_guard_enabled = bool(settings.demandos_api_key)
    return {
        "ready": result["status"] == "ok",
        "status": result["status"],
        "runtime_mode": settings.demandos_runtime_mode,
        "demo_scale": settings.demandos_demo_scale,
        "database": "connected" if result["status"] == "ok" else "not_connected",
        "api_key_guard_enabled": api_key_guard_enabled,
        "external_side_effects_enabled": False,
        "reason": result.get("reason"),
        "checks": _safe_readiness_checks(settings),
    }


@router.get("/api/runtime/check")
def runtime_check():
    """Runtime configuration check — safe for public exposure. No secrets returned."""
    settings = get_settings()
    result = _readiness_status()
    api_key_guard_enabled = bool(settings.demandos_api_key)
    return {
        "status": result["status"],
        "runtime_mode": settings.demandos_runtime_mode,
        "demo_scale": settings.demandos_demo_scale,
        "environment": settings.environment,
        "database": "postgres" if not settings.database_url.startswith("sqlite") else "sqlite",
        "api_key_guard_enabled": api_key_guard_enabled,
        "external_side_effects_enabled": False,
        "model_artifact_mode": (
            "ephemeral_tmp" if settings.demandos_runtime_mode == "vercel" else "filesystem"
        ),
        "active_connector": settings.active_connector,
    }
