"""
MonitoringService — computes model and data health metrics.

Uses existing pipeline outputs (model_metrics, stockout_risks, sales_daily, etc.)
No external calls. No credential access.

Thresholds:
  green:  relative change <= 10%
  yellow: 10% < change <= 25%
  red:    change > 25%
  unknown: no previous run to compare against
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    ModelMetric,
    StockoutRisk,
    StockoutRiskRun,
    SalesDaily,
    MonitoringRun,
    ModelDriftMetric,
    DataDriftMetric,
)
from app.utils.ids import new_id


GREEN_THRESHOLD = 0.10
YELLOW_THRESHOLD = 0.25


def _threshold_status(relative_change: float | None) -> str:
    if relative_change is None:
        return "unknown"
    abs_change = abs(relative_change)
    if abs_change <= GREEN_THRESHOLD:
        return "green"
    if abs_change <= YELLOW_THRESHOLD:
        return "yellow"
    return "red"


def _overall_status(statuses: list[str]) -> str:
    if "red" in statuses:
        return "red"
    if "yellow" in statuses:
        return "yellow"
    if all(s == "green" for s in statuses if s != "unknown"):
        if statuses:
            return "green"
    return "unknown"


class MonitoringService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self) -> dict[str, Any]:
        run_id = new_id()
        started = datetime.utcnow()

        run = MonitoringRun(
            id=run_id,
            status="running",
            started_at=started,
        )
        self.db.add(run)
        self.db.commit()

        try:
            model_metrics = self._compute_model_metrics(run_id)
            data_metrics = self._compute_data_metrics(run_id)

            model_statuses = [m["threshold_status"] for m in model_metrics]
            data_statuses = [m["threshold_status"] for m in data_metrics]

            model_health = _overall_status(model_statuses)
            data_health = _overall_status(data_statuses)
            overall = _overall_status(model_statuses + data_statuses)

            summary = {
                "model_metric_count": len(model_metrics),
                "data_metric_count": len(data_metrics),
                "model_health": model_health,
                "data_health": data_health,
            }

            self.db.query(MonitoringRun).filter(MonitoringRun.id == run_id).update({
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "model_health_status": model_health,
                "data_health_status": data_health,
                "overall_status": overall,
                "summary": summary,
            })
            self.db.commit()

            return {
                "run_id": run_id,
                "status": "completed",
                "model_health_status": model_health,
                "data_health_status": data_health,
                "overall_status": overall,
                "model_metrics": model_metrics,
                "data_metrics": data_metrics,
                "summary": summary,
                "started_at": started.isoformat(),
                "completed_at": datetime.utcnow().isoformat(),
            }

        except Exception as exc:
            self.db.rollback()
            self.db.query(MonitoringRun).filter(MonitoringRun.id == run_id).update({
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error_message": str(exc)[:500],
            })
            self.db.commit()
            raise

    # ------------------------------------------------------------------
    # Model performance monitoring
    # ------------------------------------------------------------------

    def _compute_model_metrics(self, run_id: str) -> list[dict]:
        """Compare latest overall model metrics against previous run."""
        # Get latest two overall model runs
        latest_runs = (
            self.db.query(ModelMetric)
            .filter(ModelMetric.level == "overall")
            .order_by(ModelMetric.created_at.desc())
            .limit(20)
            .all()
        )

        if not latest_runs:
            return []

        latest = latest_runs[0]
        previous = latest_runs[1] if len(latest_runs) > 1 else None

        metric_fields = [
            ("wape", latest.wape, previous.wape if previous else None),
            ("mae", latest.mae, previous.mae if previous else None),
            ("rmse", latest.rmse, previous.rmse if previous else None),
            ("bias", latest.bias, previous.bias if previous else None),
        ]

        results = []
        for name, current, prev in metric_fields:
            if current is None:
                continue
            relative = None
            if prev is not None and prev != 0:
                relative = (current - prev) / abs(prev)

            status = _threshold_status(relative)

            row = ModelDriftMetric(
                id=new_id(),
                monitoring_run_id=run_id,
                metric_name=name,
                current_value=current,
                previous_value=prev,
                relative_change_pct=round(relative * 100, 2) if relative is not None else None,
                threshold_status=status,
                model_name=latest.model_name,
                model_type=latest.model_type,
            )
            self.db.add(row)

            results.append({
                "metric_name": name,
                "current_value": current,
                "previous_value": prev,
                "relative_change_pct": round(relative * 100, 2) if relative is not None else None,
                "threshold_status": status,
                "model_name": latest.model_name,
            })

        self.db.commit()
        return results

    # ------------------------------------------------------------------
    # Data drift monitoring
    # ------------------------------------------------------------------

    def _compute_data_metrics(self, run_id: str) -> list[dict]:
        """Simple aggregate comparisons between recent and older data windows."""

        # Latest 7 days vs previous 7 days sales volume
        recent_orders = (
            self.db.query(func.sum(SalesDaily.units_sold))
            .order_by(SalesDaily.date.desc())
            .limit(7)
            .scalar() or 0.0
        )
        older_orders = (
            self.db.query(func.sum(SalesDaily.units_sold))
            .order_by(SalesDaily.date.desc())
            .offset(7)
            .limit(7)
            .scalar() or 0.0
        )

        results = []

        def _drift_metric(name: str, current: float, previous: float) -> dict:
            relative = None
            if previous != 0:
                relative = (current - previous) / abs(previous)
            status = _threshold_status(relative)
            row = DataDriftMetric(
                id=new_id(),
                monitoring_run_id=run_id,
                metric_name=name,
                current_value=current,
                previous_value=previous,
                relative_change_pct=round(relative * 100, 2) if relative is not None else None,
                threshold_status=status,
            )
            self.db.add(row)
            return {
                "metric_name": name,
                "current_value": current,
                "previous_value": previous,
                "relative_change_pct": round(relative * 100, 2) if relative is not None else None,
                "threshold_status": status,
            }

        results.append(_drift_metric("order_volume_7d", recent_orders, older_orders))

        # Stockout rate (critical + high risks) vs total
        risk_run = (
            self.db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )
        if risk_run:
            total_risks = (
                self.db.query(func.count(StockoutRisk.id))
                .filter(StockoutRisk.risk_run_id == risk_run.id)
                .scalar() or 0
            )
            high_risks = (
                self.db.query(func.count(StockoutRisk.id))
                .filter(
                    StockoutRisk.risk_run_id == risk_run.id,
                    StockoutRisk.risk_tier.in_(["critical", "high"]),
                )
                .scalar() or 0
            )
            stockout_rate = high_risks / total_risks if total_risks else 0.0
            results.append(_drift_metric("stockout_rate", stockout_rate, 0.0))

        self.db.commit()
        return results

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_latest(self) -> dict[str, Any] | None:
        run = (
            self.db.query(MonitoringRun)
            .order_by(MonitoringRun.started_at.desc())
            .first()
        )
        if not run:
            return None
        return self._serialize_run(run)

    def get_runs(self, limit: int = 20) -> list[dict]:
        runs = (
            self.db.query(MonitoringRun)
            .order_by(MonitoringRun.started_at.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize_run(r) for r in runs]

    def get_model_metrics(self, run_id: str | None = None) -> list[dict]:
        q = self.db.query(ModelDriftMetric)
        if run_id:
            q = q.filter(ModelDriftMetric.monitoring_run_id == run_id)
        else:
            latest = (
                self.db.query(MonitoringRun)
                .order_by(MonitoringRun.started_at.desc())
                .first()
            )
            if latest:
                q = q.filter(ModelDriftMetric.monitoring_run_id == latest.id)
        return [
            {
                "metric_name": m.metric_name,
                "current_value": m.current_value,
                "previous_value": m.previous_value,
                "relative_change_pct": m.relative_change_pct,
                "threshold_status": m.threshold_status,
                "model_name": m.model_name,
            }
            for m in q.all()
        ]

    def get_data_metrics(self, run_id: str | None = None) -> list[dict]:
        q = self.db.query(DataDriftMetric)
        if run_id:
            q = q.filter(DataDriftMetric.monitoring_run_id == run_id)
        else:
            latest = (
                self.db.query(MonitoringRun)
                .order_by(MonitoringRun.started_at.desc())
                .first()
            )
            if latest:
                q = q.filter(DataDriftMetric.monitoring_run_id == latest.id)
        return [
            {
                "metric_name": m.metric_name,
                "current_value": m.current_value,
                "previous_value": m.previous_value,
                "relative_change_pct": m.relative_change_pct,
                "threshold_status": m.threshold_status,
            }
            for m in q.all()
        ]

    @staticmethod
    def _serialize_run(run: MonitoringRun) -> dict:
        return {
            "run_id": run.id,
            "status": run.status,
            "model_health_status": run.model_health_status,
            "data_health_status": run.data_health_status,
            "overall_status": run.overall_status,
            "summary": run.summary or {},
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
