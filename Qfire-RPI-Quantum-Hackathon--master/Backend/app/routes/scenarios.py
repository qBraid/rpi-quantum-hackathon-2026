from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.scenario import ScenarioCreate, ScenarioResponse, ScenarioUpdate
from app.services.scenarios import create_scenario, delete_scenario, get_scenario_or_404, list_scenarios, update_scenario

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.post("", response_model=ScenarioResponse)
def create_scenario_endpoint(payload: ScenarioCreate, db: Session = Depends(get_db)):
    return create_scenario(db, payload)


@router.get("", response_model=list[ScenarioResponse])
def list_scenarios_endpoint(db: Session = Depends(get_db)):
    return list_scenarios(db)


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario_endpoint(scenario_id: str, db: Session = Depends(get_db)):
    try:
        return get_scenario_or_404(db, scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario_endpoint(scenario_id: str, payload: ScenarioUpdate, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, scenario_id)
        return update_scenario(db, scenario, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{scenario_id}", response_model=dict)
def delete_scenario_endpoint(scenario_id: str, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, scenario_id)
        delete_scenario(db, scenario)
        return {"message": "Scenario deleted"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
