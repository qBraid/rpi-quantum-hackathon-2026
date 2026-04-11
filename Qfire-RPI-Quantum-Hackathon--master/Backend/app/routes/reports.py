from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BenchmarkRun, ForecastRun, OptimizationRun, Report, RiskRun
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.reports import create_report, latest_run
from app.services.scenarios import get_scenario_or_404

router = APIRouter(prefix="/reports", tags=["reports"])


def _serialize(report: Report) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        scenario_id=report.scenario_id,
        title=report.title,
        status=report.status,
        sections=report.sections_json,
        export=report.export_json,
        created_at=report.created_at.isoformat(),
    )


def _resolve_run_for_report(db: Session, model, run_id: str | None, scenario_id: str, label: str):
    if not run_id:
        return latest_run(db, model, scenario_id)
    run = db.get(model, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"{label} run not found")
    if run.scenario_id != scenario_id:
        raise HTTPException(status_code=400, detail=f"{label} run does not belong to the selected scenario")
    return run


@router.post("/generate", response_model=ReportResponse)
def generate_report_endpoint(payload: ReportGenerateRequest, db: Session = Depends(get_db)):
    try:
        scenario = get_scenario_or_404(db, payload.scenario_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    risk_run = _resolve_run_for_report(db, RiskRun, payload.risk_run_id, scenario.id, "Risk")
    forecast_run = _resolve_run_for_report(db, ForecastRun, payload.forecast_run_id, scenario.id, "Forecast")
    optimization_run = _resolve_run_for_report(db, OptimizationRun, payload.optimization_run_id, scenario.id, "Optimization")
    benchmark_run = _resolve_run_for_report(db, BenchmarkRun, payload.benchmark_run_id, scenario.id, "Benchmark")
    return _serialize(create_report(db, scenario, payload.title, risk_run, forecast_run, optimization_run, benchmark_run))


@router.get("", response_model=list[ReportResponse])
def list_reports_endpoint(scenario_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(Report)
    if scenario_id:
        stmt = stmt.where(Report.scenario_id == scenario_id)
    stmt = stmt.order_by(desc(Report.created_at))
    return [_serialize(report) for report in db.scalars(stmt)]


@router.get("/{report_id}", response_model=ReportResponse)
def get_report_endpoint(report_id: str, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize(report)
