from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BenchmarkRun, OptimizationRun
from app.schemas.benchmark import BenchmarkRunCreate, BenchmarkRunResponse
from app.services.benchmarks import create_benchmark_run
from app.services.scenarios import get_scenario_or_404

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


def _serialize(run: BenchmarkRun) -> BenchmarkRunResponse:
    return BenchmarkRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        scenario_version=run.scenario_version,
        optimization_run_id=run.optimization_run_id,
        status=run.status,
        request=run.request_json,
        results=run.results_json,
        summary=run.summary_json,
        availability=run.availability_json,
        created_at=run.created_at.isoformat(),
    )


@router.post("/run", response_model=BenchmarkRunResponse)
def create_benchmark_run_endpoint(payload: BenchmarkRunCreate, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, payload.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    optimization_run = db.get(OptimizationRun, payload.optimization_run_id) if payload.optimization_run_id else None
    return _serialize(create_benchmark_run(db, scenario, payload.model_dump(), optimization_run))


@router.get("", response_model=list[BenchmarkRunResponse])
def list_benchmark_runs_endpoint(scenario_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(BenchmarkRun)
    if scenario_id:
        stmt = stmt.where(BenchmarkRun.scenario_id == scenario_id)
    stmt = stmt.order_by(desc(BenchmarkRun.created_at))
    return [_serialize(run) for run in db.scalars(stmt)]


@router.get("/{run_id}", response_model=BenchmarkRunResponse)
def get_benchmark_run_endpoint(run_id: str, db: Session = Depends(get_db)):
    run = db.get(BenchmarkRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return _serialize(run)
