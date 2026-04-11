from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ForecastRun
from app.schemas.forecast import ForecastRunCreate, ForecastRunResponse
from app.services.forecast import create_forecast_run
from app.services.scenarios import get_scenario_or_404

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _serialize(run: ForecastRun) -> ForecastRunResponse:
    return ForecastRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        scenario_version=run.scenario_version,
        status=run.status,
        request=run.request_json,
        snapshots=run.snapshots_json,
        summary=run.summary_json,
        diagnostics=run.diagnostics_json,
        created_at=run.created_at.isoformat(),
    )


@router.post("/run", response_model=ForecastRunResponse)
def create_forecast_run_endpoint(payload: ForecastRunCreate, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, payload.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(create_forecast_run(db, scenario, payload.model_dump()))


@router.get("/runs", response_model=list[ForecastRunResponse])
def list_forecast_runs_endpoint(scenario_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(ForecastRun)
    if scenario_id:
        stmt = stmt.where(ForecastRun.scenario_id == scenario_id)
    stmt = stmt.order_by(desc(ForecastRun.created_at))
    return [_serialize(run) for run in db.scalars(stmt)]


@router.get("/runs/{run_id}", response_model=ForecastRunResponse)
def get_forecast_run_endpoint(run_id: str, db: Session = Depends(get_db)):
    run = db.get(ForecastRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return _serialize(run)
