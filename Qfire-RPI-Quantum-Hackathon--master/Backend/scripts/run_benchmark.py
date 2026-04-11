from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Scenario  # noqa: E402
from app.services.benchmarks import create_benchmark_run  # noqa: E402
from app.services.bootstrap import seed_sample_data  # noqa: E402


def _scenario_by_selector(db, selector: str | None) -> Scenario:
    scenarios = db.query(Scenario).order_by(Scenario.created_at.asc()).all()
    if not scenarios:
        raise SystemExit("No scenarios available. Seed data or create a scenario first.")
    if not selector:
        return scenarios[0]
    for scenario in scenarios:
        if scenario.id == selector or scenario.name.lower() == selector.lower():
            return scenario
    names = ", ".join(scenario.name for scenario in scenarios)
    raise SystemExit(f"Scenario '{selector}' not found. Available scenarios: {names}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run QuantumProj's qBraid-centered benchmark workflow outside the UI.",
    )
    parser.add_argument("--scenario", help="Scenario id or exact scenario name. Defaults to the first seeded scenario.")
    parser.add_argument("--shots", type=int, default=64, help="Shot count for each execution environment.")
    parser.add_argument("--reduced-candidate-count", type=int, default=4, help="Candidate count for the reduced QAOA study.")
    parser.add_argument(
        "--environments",
        nargs="+",
        default=["ideal_simulator", "noisy_simulator"],
        choices=["ideal_simulator", "noisy_simulator", "ibm_hardware"],
        help="Execution environments to include.",
    )
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        seed_sample_data(db)
        scenario = _scenario_by_selector(db, args.scenario)
        scenario_name = scenario.name
        scenario_id = scenario.id
        run = create_benchmark_run(
            db,
            scenario,
            {
                "scenario_id": scenario.id,
                "shots": args.shots,
                "reduced_candidate_count": args.reduced_candidate_count,
                "environments": args.environments,
            },
        )

    payload = {
        "run_id": run.id,
        "status": run.status,
        "scenario": {
            "id": scenario_id,
            "name": scenario_name,
            "version": run.scenario_version,
        },
        "requested_environments": run.request_json.get("environments"),
        "availability_mode": run.availability_json.get("mode"),
        "best_strategy": run.summary_json.get("best_strategy_label"),
        "best_environment": run.summary_json.get("best_environment"),
        "recommendation": run.summary_json.get("recommendation"),
        "results": run.results_json.get("strategy_results", []),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
