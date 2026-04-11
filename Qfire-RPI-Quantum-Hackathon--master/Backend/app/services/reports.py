from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import BenchmarkRun, ForecastRun, OptimizationRun, Report, RiskRun, Scenario

logger = logging.getLogger(__name__)


def latest_run(db: Session, model, scenario_id: str):
    stmt = select(model).where(model.scenario_id == scenario_id).order_by(desc(model.created_at)).limit(1)
    return db.scalar(stmt)


def create_report(
    db: Session,
    scenario: Scenario,
    title: str,
    risk_run: RiskRun | None,
    forecast_run: ForecastRun | None,
    optimization_run: OptimizationRun | None,
    benchmark_run: BenchmarkRun | None,
) -> Report:
    risk_summary = risk_run.summary_json if risk_run else {"recommended_mode": "Not run"}
    forecast_summary = forecast_run.summary_json if forecast_run else {"containment_outlook": "Not run"}
    optimization_summary = optimization_run.summary_json if optimization_run else {"recommended_mode": "Not run"}
    benchmark_summary = benchmark_run.summary_json if benchmark_run else {"recommendation": "No benchmark available"}

    executive_lines = [
        f"Scenario {scenario.name} is currently version {scenario.version}.",
        f"Risk modeling recommends {risk_summary.get('recommended_mode', 'no mode')} execution under present constraints.",
        f"Forecast outlook is {forecast_summary.get('containment_outlook', 'unknown')} with peak ignition pressure at {forecast_summary.get('peak_ignited_cells', 'n/a')} cells.",
        f"Optimization recommends {optimization_summary.get('recommended_mode', 'no mode')} planning with connectivity reduction of {optimization_summary.get('connectivity_reduction', 'n/a')}.",
        benchmark_summary.get("recommendation", "Compiler-aware benchmark not available."),
    ]

    methodology = [
        "Risk scores compare classical, quantum, and hybrid paths over the same scenario-derived spatial features.",
        "Propagation forecast uses discrete wildfire spread steps with wind, dryness, and sensitivity controls.",
        "Optimization combines full-grid classical screening with reduced critical-subgraph quantum study.",
        "Compiler-aware benchmarking is only reported when the local environment can execute qBraid-centered runs without fabricating metrics.",
    ]

    # Build benchmark detail section
    benchmark_detail = {}
    if benchmark_run and benchmark_run.status == "complete":
        results = benchmark_run.results_json
        benchmark_detail = {
            "status": "complete",
            "circuit_type": results.get("workload", {}).get("circuit_type", "unknown"),
            "qiskit_version": benchmark_summary.get("qiskit_version"),
            "qbraid_version": benchmark_summary.get("qbraid_version"),
            "best_strategy": benchmark_summary.get("best_strategy"),
            "best_environment": benchmark_summary.get("best_environment"),
        }
    elif benchmark_run:
        benchmark_detail = {"status": benchmark_run.status, "note": "Benchmark ran in degraded or error state."}

    markdown = "\n".join(
        [
            f"# {title}",
            "",
            "## Executive summary",
            *[f"- {line}" for line in executive_lines],
            "",
            "## Methodology",
            *[f"- {line}" for line in methodology],
            "",
            "## Scenario details",
            f"- Domain: {scenario.domain}",
            f"- Description: {scenario.description or 'No description provided.'}",
            f"- Version: {scenario.version}",
            "",
            "## Benchmark integrity",
            f"- Status: {benchmark_detail.get('status', 'not run')}",
            f"- Circuit type: {benchmark_detail.get('circuit_type', 'n/a')}",
            f"- Qiskit version: {benchmark_detail.get('qiskit_version', 'n/a')}",
            f"- qBraid version: {benchmark_detail.get('qbraid_version', 'n/a')}",
            "",
        ]
    )

    report = Report(
        scenario_id=scenario.id,
        risk_run_id=risk_run.id if risk_run else None,
        forecast_run_id=forecast_run.id if forecast_run else None,
        optimization_run_id=optimization_run.id if optimization_run else None,
        benchmark_run_id=benchmark_run.id if benchmark_run else None,
        title=title,
        sections_json={
            "executive_summary": executive_lines,
            "methodology": methodology,
            "risk": risk_summary,
            "forecast": forecast_summary,
            "optimization": optimization_summary,
            "benchmark": benchmark_summary,
            "benchmark_detail": benchmark_detail,
        },
        export_json={
            "format": "markdown",
            "content": markdown,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filename": f"{scenario.name.lower().replace(' ', '-')}-report.md",
        },
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    logger.info("Report '%s' generated for scenario %s", title, scenario.id)
    return report
