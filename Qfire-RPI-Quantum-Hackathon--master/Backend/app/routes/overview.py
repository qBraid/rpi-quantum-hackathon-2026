from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import BenchmarkRun, ForecastRun, OptimizationRun, Report, RiskRun, Scenario
from app.schemas.common import HealthResponse
from app.schemas.overview import OverviewResponse
from app.services.integrations import sync_integration_statuses

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@router.get("/overview", response_model=OverviewResponse)
def overview(db: Session = Depends(get_db)):
    scenario_count = db.scalar(select(func.count()).select_from(Scenario)) or 0
    risk_count = db.scalar(select(func.count()).select_from(RiskRun)) or 0
    forecast_count = db.scalar(select(func.count()).select_from(ForecastRun)) or 0
    optimization_count = db.scalar(select(func.count()).select_from(OptimizationRun)) or 0
    benchmark_count = db.scalar(select(func.count()).select_from(BenchmarkRun)) or 0
    report_count = db.scalar(select(func.count()).select_from(Report)) or 0
    recent_benchmarks = list(db.scalars(select(BenchmarkRun).order_by(desc(BenchmarkRun.created_at)).limit(5)))
    recent_reports = list(db.scalars(select(Report).order_by(desc(Report.created_at)).limit(5)))
    integrations = sync_integration_statuses(db)
    simulator_only = any(item.provider == "ibm_quantum" and not item.available for item in integrations)

    return OverviewResponse(
        portfolio={
            "scenario_count": scenario_count,
            "risk_runs": risk_count,
            "forecast_runs": forecast_count,
            "optimization_runs": optimization_count,
            "benchmark_runs": benchmark_count,
            "report_count": report_count,
        },
        recent={
            "benchmarks": [
                {
                    "id": run.id,
                    "status": run.status,
                    "scenario_id": run.scenario_id,
                    "summary": run.summary_json,
                    "created_at": run.created_at.isoformat(),
                }
                for run in recent_benchmarks
            ],
            "reports": [{"id": report.id, "title": report.title, "created_at": report.created_at.isoformat()} for report in recent_reports],
        },
        system={
            "simulator_only": simulator_only,
            "providers": [{"provider": status.provider, "available": status.available, "mode": status.mode} for status in integrations],
        },
    )
