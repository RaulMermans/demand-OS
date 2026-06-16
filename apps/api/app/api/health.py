from fastapi import APIRouter
from app.config import get_settings
from app.schemas.api import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/api/status")
def api_status():
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
