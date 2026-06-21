"""
Observability endpoints — Sprint 11.

Read-only. No secrets, no raw DB URLs, no stack traces in responses.
Bounded query limits on all list queries.

GET /api/observability/runs-summary   — per-stage run status summary
GET /api/observability/failure-summary — latest failure per stage
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db
from app.db.models import (
    IngestionRun, AggregationRun, FeatureRun,
    ForecastRun, ModelVersion,
    StockoutRiskRun, RecommendationRun, DemoPipelineRun,
)

router = APIRouter()


def _safe_str(val) -> str | None:
    return str(val) if val is not None else None


def _ingestion_summary(db: Session) -> dict:
    run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.started_at.desc())
        .first()
    )
    if not run:
        return {"stage": "ingestion", "status": "not_run", "last_run": None}
    return {
        "stage": "ingestion",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "started_at": _safe_str(run.started_at),
            "finished_at": _safe_str(run.finished_at),
            "records_produced": run.records_produced,
        },
    }


def _aggregation_summary(db: Session) -> dict:
    run = (
        db.query(AggregationRun)
        .order_by(AggregationRun.started_at.desc())
        .first()
    )
    if not run:
        return {"stage": "aggregation", "status": "not_run", "last_run": None}
    return {
        "stage": "aggregation",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "started_at": _safe_str(run.started_at),
            "status": run.status,
        },
    }


def _feature_summary(db: Session) -> dict:
    run = (
        db.query(FeatureRun)
        .order_by(FeatureRun.started_at.desc())
        .first()
    )
    if not run:
        return {"stage": "features", "status": "not_run", "last_run": None}
    return {
        "stage": "features",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "started_at": _safe_str(run.started_at),
            "rows_created": run.rows_created,
        },
    }


def _forecast_summary(db: Session) -> dict:
    run = (
        db.query(ForecastRun)
        .order_by(ForecastRun.started_at.desc())
        .first()
    )
    if not run:
        return {"stage": "forecast", "status": "not_run", "last_run": None}
    return {
        "stage": "forecast",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "model_type": run.model_type,
            "mode": run.mode,
            "started_at": _safe_str(run.started_at),
            "rows_created": run.rows_created,
        },
    }


def _model_summary(db: Session) -> dict:
    run = (
        db.query(ModelVersion)
        .order_by(ModelVersion.created_at.desc())
        .first()
    )
    if not run:
        return {"stage": "model_training", "status": "not_run", "last_run": None}
    return {
        "stage": "model_training",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "algorithm": run.algorithm,
            "trained_at": _safe_str(run.trained_at),
        },
    }


def _risk_summary(db: Session) -> dict:
    run = (
        db.query(StockoutRiskRun)
        .order_by(StockoutRiskRun.started_at.desc())
        .first()
    )
    if not run:
        return {"stage": "stockout_risk", "status": "not_run", "last_run": None}
    return {
        "stage": "stockout_risk",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "mode": run.mode,
            "started_at": _safe_str(run.started_at),
            "rows_created": run.rows_created,
        },
    }


def _recommendation_summary(db: Session) -> dict:
    run = (
        db.query(RecommendationRun)
        .order_by(RecommendationRun.started_at.desc())
        .first()
    )
    if not run:
        return {"stage": "recommendations", "status": "not_run", "last_run": None}
    return {
        "stage": "recommendations",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "started_at": _safe_str(run.started_at),
            "rows_created": run.rows_created,
        },
    }


def _demo_pipeline_summary(db: Session) -> dict:
    run = None
    try:
        run = (
            db.query(DemoPipelineRun)
            .order_by(DemoPipelineRun.started_at.desc())
            .first()
        )
    except Exception:
        pass
    if not run:
        return {"stage": "demo_pipeline", "status": "not_run", "last_run": None}
    return {
        "stage": "demo_pipeline",
        "status": run.status or "unknown",
        "last_run": {
            "id": run.id,
            "started_at": _safe_str(run.started_at),
            "completed_at": _safe_str(run.completed_at),
        },
    }


@router.get("/observability/runs-summary")
def runs_summary(db: Session = Depends(get_db)):
    """
    Summary of the latest run for each pipeline stage.

    Read-only. Safe to expose publicly. No secrets or raw DB paths.
    """
    settings = get_settings()
    stages = [
        _ingestion_summary(db),
        _aggregation_summary(db),
        _feature_summary(db),
        _forecast_summary(db),
        _model_summary(db),
        _risk_summary(db),
        _recommendation_summary(db),
        _demo_pipeline_summary(db),
    ]
    all_ok = all(
        s["status"] in ("completed", "success", "not_run") for s in stages
    )
    any_failed = any(s["status"] == "failed" for s in stages)
    return {
        "status": "ok" if not any_failed else "degraded",
        "runtime_mode": settings.demandos_runtime_mode,
        "demo_scale": settings.demandos_demo_scale,
        "stages": stages,
    }


@router.get("/observability/failure-summary")
def failure_summary(db: Session = Depends(get_db)):
    """
    Latest failure (if any) for each pipeline stage.

    Read-only. Returns only user-safe error summaries — no raw stack traces
    or internal DB error strings in the response.
    """
    def _failed_run_info(run, stage: str) -> dict | None:
        if run is None:
            return None
        status = getattr(run, "status", None) or "unknown"
        if status not in ("failed", "error"):
            return None
        error_msg = getattr(run, "error_message", None)
        safe_msg = error_msg[:200] if error_msg else None
        return {
            "stage": stage,
            "run_id": run.id,
            "started_at": _safe_str(getattr(run, "started_at", None)),
            "error_summary": safe_msg,
        }

    failures = []

    for stage_name, model, order_col in [
        ("ingestion", IngestionRun, IngestionRun.started_at),
        ("aggregation", AggregationRun, AggregationRun.started_at),
        ("features", FeatureRun, FeatureRun.started_at),
        ("forecast", ForecastRun, ForecastRun.started_at),
        ("model_training", ModelVersion, ModelVersion.created_at),
        ("stockout_risk", StockoutRiskRun, StockoutRiskRun.started_at),
        ("recommendations", RecommendationRun, RecommendationRun.started_at),
    ]:
        run = db.query(model).order_by(order_col.desc()).first()
        info = _failed_run_info(run, stage_name)
        if info:
            failures.append(info)

    # Demo pipeline failures
    try:
        demo_run = db.query(DemoPipelineRun).order_by(DemoPipelineRun.started_at.desc()).first()
        if demo_run:
            demo_info = _failed_run_info(demo_run, "demo_pipeline")
            if demo_info:
                failures.append(demo_info)
    except Exception:
        pass

    return {
        "status": "failures_found" if failures else "clean",
        "failure_count": len(failures),
        "failures": failures[:20],
    }
