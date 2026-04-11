from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import OptimizationRun
from app.schemas.optimize import OptimizationRunCreate, OptimizationRunResponse
from app.services.optimize import create_optimization_run
from app.services.scenarios import get_scenario_or_404

router = APIRouter(prefix="/optimize", tags=["optimize"])


def _serialize(run: OptimizationRun) -> OptimizationRunResponse:
    return OptimizationRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        scenario_version=run.scenario_version,
        status=run.status,
        request=run.request_json,
        results=run.results_json,
        summary=run.summary_json,
        created_at=run.created_at.isoformat(),
    )


@router.post("/run", response_model=OptimizationRunResponse)
def create_optimization_run_endpoint(payload: OptimizationRunCreate, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, payload.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(create_optimization_run(db, scenario, payload.model_dump()))


@router.get("/runs", response_model=list[OptimizationRunResponse])
def list_optimization_runs_endpoint(scenario_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(OptimizationRun)
    if scenario_id:
        stmt = stmt.where(OptimizationRun.scenario_id == scenario_id)
    stmt = stmt.order_by(desc(OptimizationRun.created_at))
    return [_serialize(run) for run in db.scalars(stmt)]


@router.get("/runs/{run_id}", response_model=OptimizationRunResponse)
def get_optimization_run_endpoint(run_id: str, db: Session = Depends(get_db)):
    run = db.get(OptimizationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    return _serialize(run)
