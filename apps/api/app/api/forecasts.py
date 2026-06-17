"""
Forecast API routes — Sprint 4.

POST /api/forecasts/baseline/run   — run a baseline forecast + backtest
GET  /api/forecasts/runs           — list all forecast runs
GET  /api/forecasts/latest         — latest run metadata + bounded sample
GET  /api/forecasts/product/{id}   — actuals vs forecast for one product
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.db.models import ForecastRun, Forecast
from app.services.forecasting_service import ForecastingService, VALID_MODEL_TYPES

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class BaselineRunRequest(BaseModel):
    model_type: str = "seasonal_naive"
    horizon_days: int = 28
    backtest_days: int = 56
    source_feature_run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /api/forecasts/baseline/run
# ---------------------------------------------------------------------------

@router.post("/forecasts/baseline/run")
def run_baseline_forecast(
    body: BaselineRunRequest,
    db: Session = Depends(get_db),
):
    """
    Run a baseline demand forecast with historical backtesting.

    model_type options: seasonal_naive, moving_average_7d, moving_average_28d
    """
    if body.model_type not in VALID_MODEL_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid model_type '{body.model_type}'. "
                   f"Allowed: {sorted(VALID_MODEL_TYPES)}",
        )

    svc = ForecastingService(db)
    result = svc.run_baseline_forecast(
        model_type=body.model_type,
        horizon_days=body.horizon_days,
        backtest_days=body.backtest_days,
        source_feature_run_id=body.source_feature_run_id,
    )
    return result


# ---------------------------------------------------------------------------
# GET /api/forecasts/runs
# ---------------------------------------------------------------------------

@router.get("/forecasts/runs")
def list_forecast_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all forecast runs, newest first."""
    runs = (
        db.query(ForecastRun)
        .order_by(ForecastRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "run_id": r.id,
                "model_name": r.model_name,
                "model_type": r.model_type,
                "horizon_days": r.horizon_days,
                "backtest_mode": r.backtest_mode,
                "status": r.status,
                "started_at": str(r.started_at) if r.started_at else None,
                "completed_at": str(r.completed_at) if r.completed_at else None,
                "rows_created": r.rows_created or 0,
                "test_start_date": str(r.test_start_date) if r.test_start_date else None,
                "test_end_date": str(r.test_end_date) if r.test_end_date else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }


# ---------------------------------------------------------------------------
# GET /api/forecasts/latest
# ---------------------------------------------------------------------------

@router.get("/forecasts/latest")
def get_latest_forecast(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return the latest completed forecast run and a bounded sample of forecast rows."""
    run = (
        db.query(ForecastRun)
        .filter(ForecastRun.status == "completed")
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    if not run:
        return {
            "status": "no_forecast",
            "message": "No completed forecast run. POST /api/forecasts/baseline/run first.",
            "run": None,
            "sample": [],
        }

    sample_rows = (
        db.query(Forecast)
        .filter(Forecast.forecast_run_id == run.id)
        .order_by(Forecast.forecast_date, Forecast.product_id, Forecast.store_id)
        .limit(limit)
        .all()
    )

    return {
        "status": "ok",
        "run": {
            "run_id": run.id,
            "model_type": run.model_type,
            "status": run.status,
            "rows_created": run.rows_created or 0,
            "test_start_date": str(run.test_start_date) if run.test_start_date else None,
            "test_end_date": str(run.test_end_date) if run.test_end_date else None,
        },
        "sample": [_forecast_dict(f) for f in sample_rows],
        "sample_size": len(sample_rows),
    }


# ---------------------------------------------------------------------------
# GET /api/forecasts/product/{product_id}
# ---------------------------------------------------------------------------

@router.get("/forecasts/product/{product_id}")
def get_product_forecast(
    product_id: str,
    store_id: Optional[str] = Query(default=None),
    run_id: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Return actuals vs forecast for a product.

    Optional query params:
      store_id — filter to a specific store
      run_id   — use a specific forecast run (default: latest completed)
      limit    — max rows returned
    """
    if run_id:
        target_run_id = run_id
    else:
        run = (
            db.query(ForecastRun)
            .filter(ForecastRun.status == "completed")
            .order_by(ForecastRun.started_at.desc())
            .first()
        )
        if not run:
            return {
                "status": "no_forecast",
                "product_id": product_id,
                "rows": [],
            }
        target_run_id = run.id

    query = (
        db.query(Forecast)
        .filter(
            Forecast.forecast_run_id == target_run_id,
            Forecast.product_id == product_id,
        )
    )
    if store_id:
        query = query.filter(Forecast.store_id == store_id)

    rows = (
        query
        .order_by(Forecast.forecast_date, Forecast.store_id)
        .limit(limit)
        .all()
    )

    return {
        "status": "ok",
        "product_id": product_id,
        "run_id": target_run_id,
        "rows": [_forecast_dict(f) for f in rows],
        "total": len(rows),
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _forecast_dict(f: Forecast) -> dict:
    return {
        "id": f.id,
        "forecast_run_id": f.forecast_run_id,
        "forecast_date": str(f.forecast_date) if f.forecast_date else None,
        "product_id": f.product_id,
        "store_id": f.store_id,
        "horizon_day": f.horizon_day,
        "model_type": f.model_type,
        "p50_units": f.p50_units,
        "p10_units": f.p10_units,
        "p90_units": f.p90_units,
        "actual_units": f.actual_units,
        "absolute_error": f.absolute_error,
        "absolute_percentage_error": f.absolute_percentage_error,
    }
