from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Scenario
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate


def list_scenarios(db: Session) -> list[Scenario]:
    return list(db.scalars(select(Scenario).order_by(desc(Scenario.updated_at))))


def get_scenario_or_404(db: Session, scenario_id: str) -> Scenario:
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise ValueError("Scenario not found")
    return scenario


def create_scenario(db: Session, payload: ScenarioCreate) -> Scenario:
    scenario = Scenario(**payload.model_dump())
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def update_scenario(db: Session, scenario: Scenario, payload: ScenarioUpdate) -> Scenario:
    changed = False
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(scenario, key, value)
        changed = True
    if changed:
        scenario.version += 1
    db.commit()
    db.refresh(scenario)
    return scenario


def delete_scenario(db: Session, scenario: Scenario) -> None:
    db.delete(scenario)
    db.commit()
