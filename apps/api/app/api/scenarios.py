"""
Scenario planning API — what-if simulation.

All scenario outputs are clearly labelled as simulated.
Scenarios never mutate canonical forecast/risk/recommendation tables.

Endpoints:
  POST /api/scenarios/run            — run a scenario (API key required)
  GET  /api/scenarios/runs           — list scenario runs
  GET  /api/scenarios/runs/latest    — latest scenario run
  GET  /api/scenarios/{scenario_id}  — single scenario
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import require_api_key
from app.db.session import get_db
from app.schemas.scenarios import ScenarioInputs
from app.services.scenario_service import ScenarioService

router = APIRouter()


@router.post("/scenarios/run")
def run_scenario(
    inputs: ScenarioInputs,
    db: Session = Depends(get_db),
    _: None = Depends(require_api_key),
) -> dict:
    """
    Run a what-if scenario simulation.

    Results are stored in scenario_runs / scenario_results tables only.
    Canonical pipeline tables are never mutated.
    All outputs are labelled simulated=true.
    """
    service = ScenarioService(db)
    return service.run(inputs)


@router.get("/scenarios/runs")
def get_scenario_runs(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    service = ScenarioService(db)
    runs = service.get_runs(limit=limit)
    return {"runs": runs, "total": len(runs), "simulated": True}


@router.get("/scenarios/runs/latest")
def get_latest_scenario(db: Session = Depends(get_db)) -> dict:
    service = ScenarioService(db)
    result = service.get_latest()
    if not result:
        return {"has_scenario_run": False, "latest_run": None, "simulated": True}
    return {"has_scenario_run": True, "latest_run": result, "simulated": True}


@router.get("/scenarios/{scenario_id}")
def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
) -> dict:
    service = ScenarioService(db)
    result = service.get_by_id(scenario_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return result
