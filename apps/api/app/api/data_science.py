"""
Data science summary API routes — Sprint 15.

All endpoints are read-only. No data is mutated.
No secrets are exposed. No external services are called.

GET /api/data-science/summary
GET /api/data-science/forecast-diagnostics
GET /api/data-science/model-comparison
GET /api/data-science/feature-signals
GET /api/data-science/business-impact
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.data_science import (
    DataScienceSummaryResponse,
    ForecastDiagnosticsResponse,
    ModelComparisonResponse,
    FeatureSignalsResponse,
    BusinessImpactResponse,
)
from app.services.data_science_summary_service import DataScienceSummaryService

router = APIRouter()


@router.get("/data-science/summary", response_model=DataScienceSummaryResponse)
def get_data_science_summary(db: Session = Depends(get_db)):
    """
    High-level ML workflow status.

    Returns pipeline story, data volumes, latest model status, and decision
    summary derived from existing pipeline tables. Read-only.
    """
    return DataScienceSummaryService(db).get_summary()


@router.get("/data-science/forecast-diagnostics", response_model=ForecastDiagnosticsResponse)
def get_forecast_diagnostics(db: Session = Depends(get_db)):
    """
    Model diagnostics for the latest baseline and ML forecast runs.

    Returns MAE, RMSE, WAPE, Bias with business-friendly interpretation.
    Handles no-data state gracefully. Read-only.
    """
    return DataScienceSummaryService(db).get_forecast_diagnostics()


@router.get("/data-science/model-comparison", response_model=ModelComparisonResponse)
def get_model_comparison(db: Session = Depends(get_db)):
    """
    Side-by-side comparison of all completed forecast model runs.

    Ranks models by WAPE (lower is better). Returns strengths, limitations,
    and best-use guidance for each model. Read-only.
    """
    return DataScienceSummaryService(db).get_model_comparison()


@router.get("/data-science/feature-signals", response_model=FeatureSignalsResponse)
def get_feature_signals(db: Session = Depends(get_db)):
    """
    Grouped feature signal explanations for the demand forecasting model.

    Uses the trained model's feature column list when available; falls back
    to the canonical feature definition. Returns grouped interpretations.
    Read-only. Does not claim precise causal attribution.
    """
    return DataScienceSummaryService(db).get_feature_signals()


@router.get("/data-science/business-impact", response_model=BusinessImpactResponse)
def get_business_impact(db: Session = Depends(get_db)):
    """
    Decision-level business impact summary.

    Returns risk tier distribution, recommendation urgency distribution,
    top 5 risks, top 5 recommendations, and review guidance.
    Read-only. No purchase orders are created.
    """
    return DataScienceSummaryService(db).get_business_impact()
