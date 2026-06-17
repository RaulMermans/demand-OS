from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import health, ingestion, forecasts, risks, recommendations, metrics, overview
from app.api import demo, aggregation
from app.db.session import init_db

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "DemandOS — demand forecasting and inventory risk platform. "
        "Sprint 2: raw ingestion + canonical daily aggregation active."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(health.router,           tags=["health"])
app.include_router(ingestion.router,        prefix="/api", tags=["ingestion"])
app.include_router(demo.router,             prefix="/api", tags=["demo"])
app.include_router(forecasts.router,        prefix="/api", tags=["forecasts"])
app.include_router(risks.router,            prefix="/api", tags=["risks"])
app.include_router(recommendations.router,  prefix="/api", tags=["recommendations"])
app.include_router(metrics.router,          prefix="/api", tags=["metrics"])
app.include_router(overview.router,         prefix="/api", tags=["overview"])
app.include_router(aggregation.router,      prefix="/api", tags=["aggregation"])
