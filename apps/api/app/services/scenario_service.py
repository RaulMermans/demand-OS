"""
ScenarioService — what-if simulation against current pipeline baseline.

Rules:
- Never mutates forecast/risk/recommendation canonical tables.
- Uses latest stockout risk run as baseline.
- Applies multipliers to produce simulated risk metrics.
- All outputs are stored in scenario_runs / scenario_results tables only.
- Clearly labelled as simulated in all outputs.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    StockoutRisk,
    StockoutRiskRun,
    ScenarioRun,
    ScenarioResult,
)
from app.schemas.scenarios import ScenarioInputs
from app.utils.ids import new_id


class ScenarioService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, inputs: ScenarioInputs) -> dict[str, Any]:
        scenario_id = new_id()
        started = datetime.utcnow()

        run = ScenarioRun(
            id=scenario_id,
            status="running",
            started_at=started,
            inputs=inputs.model_dump(),
        )
        self.db.add(run)
        self.db.commit()

        try:
            result = self._simulate(scenario_id, inputs)

            self.db.query(ScenarioRun).filter(ScenarioRun.id == scenario_id).update({
                "status": "completed",
                "completed_at": datetime.utcnow(),
                "baseline_summary": result["baseline_summary"],
                "scenario_summary": result["scenario_summary"],
                "delta_lost_sales": result["delta_lost_sales"],
                "delta_order_cost": result["delta_order_cost"],
                "delta_high_risk_count": result["delta_high_risk_count"],
                "delta_critical_risk_count": result["delta_critical_risk_count"],
                "top_impacted": result["top_impacted_product_stores"],
            })
            self.db.commit()
            return result

        except Exception as exc:
            self.db.rollback()
            self.db.query(ScenarioRun).filter(ScenarioRun.id == scenario_id).update({
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error_message": str(exc)[:500],
            })
            self.db.commit()
            raise

    def _simulate(self, scenario_id: str, inputs: ScenarioInputs) -> dict[str, Any]:
        risk_run = (
            self.db.query(StockoutRiskRun)
            .filter(StockoutRiskRun.status == "completed")
            .order_by(StockoutRiskRun.started_at.desc())
            .first()
        )

        if not risk_run:
            return self._empty_result(scenario_id, inputs)

        risks = (
            self.db.query(StockoutRisk)
            .filter(StockoutRisk.risk_run_id == risk_run.id)
            .all()
        )

        baseline_high = sum(1 for r in risks if r.risk_tier in ("high",))
        baseline_critical = sum(1 for r in risks if r.risk_tier == "critical")
        baseline_lost_sales = sum(r.lost_sales_value_estimate or 0.0 for r in risks)
        baseline_order_cost = 0.0  # not in risk table; estimated below

        scenario_results = []
        scen_high = 0
        scen_critical = 0
        scen_lost_sales = 0.0
        scen_order_cost = 0.0
        deltas = []

        for r in risks:
            # Apply demand multiplier to forecast
            sim_demand_p50 = (r.forecast_demand_p50 or 0.0) * inputs.demand_multiplier
            sim_demand_p90 = (r.forecast_demand_p90 or 0.0) * inputs.demand_multiplier

            # Apply lead time multiplier
            sim_lead_time = int((r.supplier_lead_time_days or 14) * inputs.lead_time_multiplier)

            # Apply inventory adjustment
            sim_available = (r.current_available_units or 0.0) + inputs.inventory_adjustment_units

            # Simplified days of supply
            avg_daily = (r.average_daily_forecast or 0.01) * inputs.demand_multiplier
            sim_dos = sim_available / avg_daily if avg_daily > 0 else 999.0

            # Simulate risk tier from days of supply
            if sim_dos <= sim_lead_time * 1.1:
                sim_tier = "critical"
                scen_critical += 1
            elif sim_dos <= sim_lead_time * 1.5:
                sim_tier = "high"
                scen_high += 1
            elif sim_dos <= sim_lead_time * 2.5:
                sim_tier = "medium"
            else:
                sim_tier = "low"

            # Simulate lost sales (crude estimate)
            shortfall = max(0.0, sim_demand_p50 - sim_available)
            sim_lost = shortfall * (r.lost_sales_value_estimate or 0.0) / max(sim_demand_p50, 1.0)
            scen_lost_sales += sim_lost

            delta_dos = sim_dos - (r.days_of_supply or 0.0)
            delta_lost = sim_lost - (r.lost_sales_value_estimate or 0.0)

            deltas.append({
                "product_id": r.product_id,
                "store_id": r.store_id,
                "baseline_risk_tier": r.risk_tier,
                "scenario_risk_tier": sim_tier,
                "delta_days_of_supply": round(delta_dos, 2),
                "delta_lost_sales": round(delta_lost, 2),
                "abs_delta": abs(delta_lost),
            })

            scenario_results.append(ScenarioResult(
                id=new_id(),
                scenario_run_id=scenario_id,
                product_id=r.product_id,
                store_id=r.store_id,
                baseline_risk_tier=r.risk_tier,
                scenario_risk_tier=sim_tier,
                baseline_days_of_supply=r.days_of_supply,
                scenario_days_of_supply=round(sim_dos, 2),
                baseline_lost_sales=r.lost_sales_value_estimate or 0.0,
                scenario_lost_sales=round(sim_lost, 2),
                baseline_order_cost=0.0,
                scenario_order_cost=0.0,
                delta_days_of_supply=round(delta_dos, 2),
                delta_lost_sales=round(delta_lost, 2),
                delta_order_cost=0.0,
            ))

        # Bulk insert results
        for row in scenario_results:
            self.db.add(row)
        self.db.commit()

        # Top impacted (by abs delta lost sales)
        deltas.sort(key=lambda x: x["abs_delta"], reverse=True)
        top = [
            {k: v for k, v in d.items() if k != "abs_delta"}
            for d in deltas[:10]
        ]

        baseline_summary = {
            "total_product_stores": len(risks),
            "high_risk_count": baseline_high,
            "critical_risk_count": baseline_critical,
            "total_lost_sales_estimate": round(baseline_lost_sales, 2),
            "total_order_cost_estimate": 0.0,
        }
        scenario_summary = {
            "total_product_stores": len(risks),
            "high_risk_count": scen_high,
            "critical_risk_count": scen_critical,
            "total_lost_sales_estimate": round(scen_lost_sales, 2),
            "total_order_cost_estimate": 0.0,
        }

        return {
            "scenario_id": scenario_id,
            "status": "completed",
            "inputs": inputs.model_dump(),
            "baseline_summary": baseline_summary,
            "scenario_summary": scenario_summary,
            "delta_lost_sales": round(scen_lost_sales - baseline_lost_sales, 2),
            "delta_order_cost": 0.0,
            "delta_high_risk_count": scen_high - baseline_high,
            "delta_critical_risk_count": scen_critical - baseline_critical,
            "top_impacted_product_stores": top,
            "created_at": datetime.utcnow().isoformat(),
            "simulated": True,
        }

    @staticmethod
    def _empty_result(scenario_id: str, inputs: ScenarioInputs) -> dict[str, Any]:
        empty_summary = {
            "total_product_stores": 0,
            "high_risk_count": 0,
            "critical_risk_count": 0,
            "total_lost_sales_estimate": 0.0,
            "total_order_cost_estimate": 0.0,
        }
        return {
            "scenario_id": scenario_id,
            "status": "completed",
            "inputs": inputs.model_dump(),
            "baseline_summary": empty_summary,
            "scenario_summary": empty_summary,
            "delta_lost_sales": 0.0,
            "delta_order_cost": 0.0,
            "delta_high_risk_count": 0,
            "delta_critical_risk_count": 0,
            "top_impacted_product_stores": [],
            "created_at": datetime.utcnow().isoformat(),
            "simulated": True,
        }

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_runs(self, limit: int = 20) -> list[dict]:
        runs = (
            self.db.query(ScenarioRun)
            .order_by(ScenarioRun.started_at.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize_run(r) for r in runs]

    def get_latest(self) -> dict[str, Any] | None:
        run = (
            self.db.query(ScenarioRun)
            .order_by(ScenarioRun.started_at.desc())
            .first()
        )
        if not run:
            return None
        return self._serialize_run(run)

    def get_by_id(self, scenario_id: str) -> dict[str, Any] | None:
        run = self.db.query(ScenarioRun).filter(ScenarioRun.id == scenario_id).first()
        if not run:
            return None
        return self._serialize_run(run)

    @staticmethod
    def _serialize_run(run: ScenarioRun) -> dict:
        return {
            "scenario_id": run.id,
            "status": run.status,
            "inputs": run.inputs or {},
            "baseline_summary": run.baseline_summary or {},
            "scenario_summary": run.scenario_summary or {},
            "delta_lost_sales": run.delta_lost_sales,
            "delta_order_cost": run.delta_order_cost,
            "delta_high_risk_count": run.delta_high_risk_count,
            "delta_critical_risk_count": run.delta_critical_risk_count,
            "top_impacted_product_stores": run.top_impacted or [],
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "simulated": True,
        }
