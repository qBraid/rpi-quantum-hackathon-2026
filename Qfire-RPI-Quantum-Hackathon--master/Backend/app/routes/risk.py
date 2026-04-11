from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RiskRun
from app.schemas.risk import RiskRunCreate, RiskRunResponse
from app.services.risk import create_risk_run
from app.services.scenarios import get_scenario_or_404

router = APIRouter(prefix="/risk", tags=["risk"])


def _serialize(run: RiskRun) -> RiskRunResponse:
    return RiskRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        scenario_version=run.scenario_version,
        status=run.status,
        modes=run.modes_json,
        request=run.request_json,
        results=run.results_json,
        summary=run.summary_json,
        created_at=run.created_at.isoformat(),
    )


@router.post("/run", response_model=RiskRunResponse)
def create_risk_run_endpoint(payload: RiskRunCreate, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, payload.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(create_risk_run(db, scenario, payload.model_dump()))


@router.get("/runs", response_model=list[RiskRunResponse])
def list_risk_runs_endpoint(scenario_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(RiskRun)
    if scenario_id:
        stmt = stmt.where(RiskRun.scenario_id == scenario_id)
    stmt = stmt.order_by(desc(RiskRun.created_at))
    return [_serialize(run) for run in db.scalars(stmt)]


@router.get("/runs/{run_id}", response_model=RiskRunResponse)
def get_risk_run_endpoint(run_id: str, db: Session = Depends(get_db)):
    run = db.get(RiskRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Risk run not found")
    return _serialize(run)
