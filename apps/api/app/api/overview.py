from fastapi import APIRouter
from app.schemas.api import OverviewResponse, DataHealthResponse

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def get_overview():
    """
    Operational overview: pipeline status, record counts, high-level risk summary.
    Sprint 2 TODO: query DB for live counts and risk tier breakdown.
    """
    return OverviewResponse(
        status="scaffold_ready",
        data_mode="not_seeded",
        pipeline_ready=False,
        message=(
            "Overview will show live metrics after Sprint 1 data seeding "
            "and Sprint 2 aggregation pipeline."
        ),
        summary={
            "products": 0,
            "stores": 0,
            "orders_last_30d": 0,
            "critical_risks": 0,
            "pending_recommendations": 0,
            "last_ingestion_run": None,
            "last_forecast_run": None,
        },
    )


@router.get("/data-health", response_model=DataHealthResponse)
def get_data_health():
    """
    Data quality report: validation error counts, missing data gaps, schema drift.
    Sprint 1 TODO: run validation checks and return results.
    """
    return DataHealthResponse(
        status="scaffold_ready",
        data_mode="not_seeded",
        checks=[
            {
                "check": "raw_products_present",
                "passed": False,
                "message": "No data ingested yet.",
            },
            {
                "check": "raw_orders_present",
                "passed": False,
                "message": "No data ingested yet.",
            },
            {
                "check": "raw_inventory_present",
                "passed": False,
                "message": "No data ingested yet.",
            },
            {
                "check": "no_orphaned_order_lines",
                "passed": False,
                "message": "Cannot check — no data ingested yet.",
            },
        ],
        message=(
            "Data health checks will run automatically after Sprint 1 ingestion."
        ),
    )
