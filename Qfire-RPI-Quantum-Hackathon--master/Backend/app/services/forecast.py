from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.algorithms.shift import build_shift_diagnostics
from app.models import ForecastRun, Scenario
from app.services.wildfire_model import build_environment, default_environment, run_stochastic_forecast

logger = logging.getLogger(__name__)


def create_forecast_run(db: Session, scenario: Scenario, payload: dict) -> ForecastRun:
    logger.info("Running ensemble wildfire forecast for scenario %s", scenario.id)
    base_environment = default_environment(scenario)
    environment = build_environment(
        base_environment,
        dryness=payload["dryness"],
        spread_sensitivity=payload["spread_sensitivity"],
        wind_direction=payload["wind_direction"],
        wind_speed=payload.get("wind_speed", base_environment["wind_speed"]),
        slope_influence=payload.get("slope_influence", base_environment["slope_influence"]),
        spotting_likelihood=payload.get("spotting_likelihood", base_environment["spotting_likelihood"]),
    )
    ensemble_runs = int(payload.get("ensemble_runs", base_environment["ensemble_runs"]))
    forecast = run_stochastic_forecast(
        scenario.grid,
        environment=environment,
        steps=payload["steps"],
        seed=int(payload.get("seed", 17)),
        runs=ensemble_runs,
    )
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "planning_grade_note": "Planning-grade comparative decision support. Results are stochastic ensemble summaries, not operational fire behavior predictions.",
        "ensemble_runs": ensemble_runs,
        "peak_burn_probability": forecast["summary"]["peak_burn_probability"],
        "mean_final_burned_area": forecast["summary"]["mean_final_burned_area"],
        "burned_area_p90": forecast["summary"]["p90_final_burned_area"],
        "peak_ignited_cells": max((snap["metrics"]["burning_cells"] for snap in forecast["representative_snapshots"]), default=0),
        "final_affected_cells": forecast["summary"]["p50_final_burned_area"],
        "containment_outlook": "stressed" if forecast["summary"]["p90_final_burned_area"] >= 35 else "watch" if forecast["summary"]["p50_final_burned_area"] >= 18 else "manageable",
        "likely_spread_corridors": forecast["summary"]["likely_spread_corridors"],
    }
    run = ForecastRun(
        scenario_id=scenario.id,
        scenario_version=scenario.version,
        request_json={**payload, "ensemble_runs": ensemble_runs},
        snapshots_json=forecast["representative_snapshots"],
        diagnostics_json={
            **build_shift_diagnostics(len(scenario.grid), payload["steps"]),
            "ensemble": {
                "burn_probability_map": forecast["burn_probability_map"],
                "expected_ignition_time_map": forecast["expected_ignition_time_map"],
                "final_burned_area_distribution": forecast["final_burned_area_distribution"],
            },
        },
        summary_json=summary,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info("Forecast run %s complete with %d ensemble runs", run.id, ensemble_runs)
    return run
