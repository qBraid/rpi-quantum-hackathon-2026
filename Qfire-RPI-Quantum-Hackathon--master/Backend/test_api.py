from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parent))

from app.main import app  # noqa: E402


client = TestClient(app)


def _first_scenario_id() -> str:
    response = client.get("/api/scenarios")
    response.raise_for_status()
    scenarios = response.json()
    assert scenarios
    return scenarios[0]["id"]


def test_scenario_crud():
    payload = {
        "name": "Test Wildfire Grid",
        "domain": "wildfire",
        "status": "draft",
        "description": "Test scenario",
        "grid": [["empty" for _ in range(10)] for _ in range(10)],
        "metadata_json": {"region": "test"},
        "constraints_json": {"intervention_budget_k": 5},
        "objectives_json": {"primary": "minimize exposure"},
    }
    created = client.post("/api/scenarios", json=payload)
    assert created.status_code == 200
    scenario_id = created.json()["id"]

    updated = client.patch(f"/api/scenarios/{scenario_id}", json={"status": "active"})
    assert updated.status_code == 200
    assert updated.json()["version"] >= 2

    deleted = client.delete(f"/api/scenarios/{scenario_id}")
    assert deleted.status_code == 200


def test_core_flow_endpoints():
    scenario_id = _first_scenario_id()

    risk = client.post("/api/risk/run", json={"scenario_id": scenario_id, "horizon_steps": 2, "sample_count": 12})
    assert risk.status_code == 200
    risk_id = risk.json()["id"]
    assert risk.json()["summary"]["classification_task"]
    assert risk.json()["summary"]["dataset"]["feature_names"]
    assert risk.json()["results"]["classical"]["model"]["family"] == "logistic_regression"
    assert risk.json()["results"]["quantum"]["model"]["family"] == "variational_quantum_classifier"
    risk_list = client.get(f"/api/risk/runs?scenario_id={scenario_id}")
    assert risk_list.status_code == 200
    assert any(item["id"] == risk_id for item in risk_list.json())

    forecast = client.post("/api/forecast/run", json={"scenario_id": scenario_id})
    assert forecast.status_code == 200
    assert len(forecast.json()["snapshots"]) >= 2
    forecast_id = forecast.json()["id"]
    forecast_list = client.get(f"/api/forecast/runs?scenario_id={scenario_id}")
    assert forecast_list.status_code == 200
    assert any(item["id"] == forecast_id for item in forecast_list.json())

    optimize = client.post("/api/optimize/run", json={"scenario_id": scenario_id})
    assert optimize.status_code == 200
    optimize_id = optimize.json()["id"]
    assert optimize.json()["summary"]["mode"] == "planning"
    optimize_list = client.get(f"/api/optimize/runs?scenario_id={scenario_id}")
    assert optimize_list.status_code == 200
    assert any(item["id"] == optimize_id for item in optimize_list.json())

    challenge_optimize = client.post("/api/optimize/run", json={"scenario_id": scenario_id, "mode": "challenge"})
    assert challenge_optimize.status_code == 200
    assert challenge_optimize.json()["summary"]["mode"] == "challenge"
    assert "challenge_cost_after" in challenge_optimize.json()["summary"]

    benchmark = client.post(
        "/api/benchmarks/run",
        json={"scenario_id": scenario_id, "optimization_run_id": optimize_id, "environments": ["ideal_simulator", "noisy_simulator"]},
    )
    assert benchmark.status_code == 200
    benchmark_id = benchmark.json()["id"]
    assert benchmark.json()["availability"]["mode"] in {"ready", "degraded"}
    if benchmark.json()["status"] == "complete":
        strategy_results = benchmark.json()["results"]["strategy_results"]
        assert len(strategy_results) >= 4
        assert "total_gates" in strategy_results[0]["compiled_metrics"]
        assert "success_probability" in strategy_results[0]["output_quality"]

    report = client.post(
        "/api/reports/generate",
        json={"scenario_id": scenario_id, "risk_run_id": risk_id, "benchmark_run_id": benchmark_id},
    )
    assert report.status_code == 200
    assert report.json()["export"]["format"] == "markdown"
    reports = client.get(f"/api/reports?scenario_id={scenario_id}")
    assert reports.status_code == 200
    assert reports.json()


def test_integrations_and_overview():
    integrations = client.get("/api/integrations/status")
    assert integrations.status_code == 200
    assert integrations.json()["providers"]

    overview = client.get("/api/overview")
    assert overview.status_code == 200
    assert "portfolio" in overview.json()
