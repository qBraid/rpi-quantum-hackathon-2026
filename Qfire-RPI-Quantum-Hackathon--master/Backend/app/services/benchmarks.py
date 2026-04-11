from __future__ import annotations

import importlib.metadata
import importlib.util
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.algorithms.qaoa import (
    QAOAProblem,
    approximation_ratio,
    brute_force_best,
    brute_force_worst,
    build_qaoa_circuit,
    circuit_metrics,
    parse_counts,
    qaoa_level1,
    run_transpiled_qaoa,
)
from app.core.config import settings
from app.models import BenchmarkRun, OptimizationRun, Scenario
from app.services.optimize import candidate_rows
from app.services.spatial import neighbors
from app.services.wildfire_model import build_environment, default_environment


@dataclass(frozen=True)
class BenchmarkStrategy:
    key: str
    label: str
    description: str
    intermediate_representation: str
    compile_profile: str
    basis_gates: tuple[str, ...]
    optimization_level: int
    layout_method: str | None
    routing_method: str | None
    coupling_profile: str
    portability_note: str


PORTABLE_QASM2_STRATEGY = BenchmarkStrategy(
    key="qbraid_qasm2_portable",
    label="Portable OpenQASM 2 bridge",
    description="Normalizes the QAOA workload through qBraid OpenQASM 2 and compiles it to a generic line topology with CX gates. This emphasizes portability over hardware specificity.",
    intermediate_representation="qasm2",
    compile_profile="generic_line_cx",
    basis_gates=("rz", "sx", "x", "cx"),
    optimization_level=1,
    layout_method="trivial",
    routing_method="sabre",
    coupling_profile="line_topology",
    portability_note="Portable canonical form that can be executed on simulators and later retargeted to hardware.",
)

TARGET_AWARE_QASM3_STRATEGY = BenchmarkStrategy(
    key="qbraid_qasm3_target_aware",
    label="Target-aware OpenQASM 3 bridge",
    description="Normalizes the QAOA workload through qBraid OpenQASM 3 and compiles it against a heavy-hex-like constrained target with ECR-style two-qubit operations. This favors realistic hardware preparation.",
    intermediate_representation="qasm3",
    compile_profile="heavy_hex_ecr_target",
    basis_gates=("rz", "sx", "x", "ecr"),
    optimization_level=2,
    layout_method="dense",
    routing_method="sabre",
    coupling_profile="heavy_hex_target",
    portability_note="Target-aware constrained preparation designed to mirror IBM-style connectivity pressure before hardware execution.",
)


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except Exception:
        return None


def _build_problem(grid: list[list[str]], reduced_count: int, environment: dict) -> tuple[list[dict], QAOAProblem]:
    candidates = candidate_rows(grid, environment)[:reduced_count]
    weights = [round(float(row["score"]), 4) for row in candidates]
    penalties: dict[tuple[int, int], float] = {}
    for idx, candidate in enumerate(candidates):
        adjacent = {(r, c) for r, c in neighbors(candidate["row"], candidate["col"], len(grid))}
        for jdx in range(idx + 1, len(candidates)):
            other = candidates[jdx]
            if (other["row"], other["col"]) in adjacent:
                penalties[(idx, jdx)] = 0.28
    budget = max(2, min(5, len(candidates) // 2))
    return candidates, QAOAProblem(weights=weights, pair_penalties=penalties, budget=budget)


def _qasm3_bridge_ready() -> bool:
    return _module_available("qiskit_qasm3_import")


def _ibm_runtime_available() -> bool:
    if not (settings.ibm_configured and _module_available("qiskit_ibm_runtime")):
        return False
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService

        service_kwargs = {"token": settings.ibm_token}
        if settings.ibm_instance:
            service_kwargs["instance"] = settings.ibm_instance
        if settings.normalized_ibm_channel:
            service_kwargs["channel"] = settings.normalized_ibm_channel
        service = QiskitRuntimeService(**service_kwargs)
        backends = service.backends(simulator=False)
        return any(backends)
    except Exception:
        return False


def benchmark_availability(requested_environments: list[str] | None = None) -> dict:
    qbraid_installed = _module_available("qbraid")
    qiskit_installed = _module_available("qiskit")
    aer_installed = _module_available("qiskit_aer")
    qasm3_ready = _qasm3_bridge_ready()
    runtime_installed = _module_available("qiskit_ibm_runtime")
    needs_ibm_check = requested_environments is None or "ibm_hardware" in requested_environments
    ibm_execution_ready = _ibm_runtime_available() if needs_ibm_check else False
    compiler_ready = qbraid_installed and qiskit_installed and aer_installed and qasm3_ready
    return {
        "qbraid_sdk_installed": qbraid_installed,
        "qbraid_version": _version("qbraid"),
        "qiskit_installed": qiskit_installed,
        "qiskit_version": _version("qiskit"),
        "qiskit_aer_installed": aer_installed,
        "qiskit_aer_version": _version("qiskit-aer"),
        "qiskit_qasm3_import_installed": qasm3_ready,
        "qiskit_qasm3_import_version": _version("qiskit-qasm3-import"),
        "qiskit_ibm_runtime_installed": runtime_installed,
        "qiskit_ibm_runtime_version": _version("qiskit-ibm-runtime"),
        "qbraid_api_key_configured": settings.qbraid_configured,
        "ibm_token_configured": settings.ibm_configured,
        "compiler_aware_benchmarking_ready": compiler_ready,
        "ibm_execution_ready": ibm_execution_ready,
        "strategy_count": 2 if compiler_ready else 0,
        "mode": "ready" if compiler_ready else "degraded",
        "reason": None
        if compiler_ready
        else "Install qbraid, qiskit, qiskit-aer, and qiskit-qasm3-import to execute the two-strategy compiler-aware benchmark study.",
    }


def _conversion_path(source: str, target: str) -> list[str]:
    from qbraid import ConversionGraph

    graph = ConversionGraph()
    path = graph.find_shortest_conversion_path(source, target)
    labels: list[str] = []
    for step in path:
        owner = getattr(step, "__self__", None)
        if owner is None:
            labels.append(str(step))
        else:
            labels.append(f"{owner.source} -> {owner.target}")
    return labels


def _qbraid_roundtrip(circuit, intermediate_representation: str):
    from qbraid import transpile as qbraid_transpile

    bridged_program = qbraid_transpile(circuit, intermediate_representation)
    normalized_circuit = qbraid_transpile(bridged_program, "qiskit")
    return normalized_circuit, {
        "source_representation": "qiskit.QuantumCircuit",
        "intermediate_representation": intermediate_representation,
        "forward_path": _conversion_path("qiskit", intermediate_representation),
        "reverse_path": _conversion_path(intermediate_representation, "qiskit"),
        "qbraid_usage": [
            f"qbraid.transpile(workload, '{intermediate_representation}')",
            "qbraid.transpile(intermediate_program, 'qiskit')",
        ],
    }


def _portable_compile(circuit):
    from qiskit import transpile as qiskit_transpile
    from qiskit.transpiler import CouplingMap

    return qiskit_transpile(
        circuit,
        basis_gates=list(PORTABLE_QASM2_STRATEGY.basis_gates),
        coupling_map=CouplingMap.from_line(circuit.num_qubits),
        optimization_level=PORTABLE_QASM2_STRATEGY.optimization_level,
        layout_method=PORTABLE_QASM2_STRATEGY.layout_method,
        routing_method=PORTABLE_QASM2_STRATEGY.routing_method,
    )


def _target_aware_compile(circuit):
    from qiskit import transpile as qiskit_transpile
    from qiskit.transpiler import CouplingMap

    heavy_hex = CouplingMap.from_heavy_hex(3)
    return qiskit_transpile(
        circuit,
        basis_gates=list(TARGET_AWARE_QASM3_STRATEGY.basis_gates),
        coupling_map=heavy_hex,
        optimization_level=TARGET_AWARE_QASM3_STRATEGY.optimization_level,
        layout_method=TARGET_AWARE_QASM3_STRATEGY.layout_method,
        routing_method=TARGET_AWARE_QASM3_STRATEGY.routing_method,
    )


def _select_ibm_backend(required_qubits: int):
    from qiskit_ibm_runtime import QiskitRuntimeService

    service_kwargs = {"token": settings.ibm_token}
    if settings.ibm_instance:
        service_kwargs["instance"] = settings.ibm_instance
    if settings.normalized_ibm_channel:
        service_kwargs["channel"] = settings.normalized_ibm_channel
    service = QiskitRuntimeService(**service_kwargs)
    candidates = service.backends(simulator=False, operational=True, min_num_qubits=required_qubits)
    if not candidates:
        raise RuntimeError(f"No IBM hardware backend available with at least {required_qubits} qubits.")
    return min(candidates, key=lambda item: (getattr(item.status(), "pending_jobs", 10**9), item.num_qubits))


def _ibm_sampler_counts(problem: QAOAProblem, isa_circuit, shots: int, backend) -> dict:
    from qiskit_ibm_runtime import SamplerV2

    sampler = SamplerV2(mode=backend)
    job = sampler.run([isa_circuit], shots=shots)
    result = job.result()[0]
    data_bin = result.data
    bit_array = None
    for key in data_bin.keys():
        candidate = getattr(data_bin, key)
        if hasattr(candidate, "get_counts"):
            bit_array = candidate
            break
    if bit_array is None:
        raise RuntimeError("IBM Sampler result did not contain a count-bearing classical register.")
    raw_counts = bit_array.get_counts()
    parsed, expected_cost, success_probability = parse_counts(problem, raw_counts)
    return {
        "counts": parsed,
        "expected_cost": expected_cost,
        "success_probability": success_probability,
        "approximation_ratio": approximation_ratio(problem, expected_cost),
        "unique_outcomes": len(parsed),
        "job_id": job.job_id(),
        "backend_name": backend.name,
        "queue_depth_at_submission": getattr(backend.status(), "pending_jobs", None),
    }


def _resource_delta(compiled_metrics: dict, baseline_metrics: dict) -> dict:
    return {
        "depth_delta": compiled_metrics["depth"] - baseline_metrics["depth"],
        "two_qubit_gate_delta": compiled_metrics["two_qubit_gate_count"] - baseline_metrics["two_qubit_gate_count"],
        "total_gate_delta": compiled_metrics["total_gates"] - baseline_metrics["total_gates"],
    }


def _annotate_metrics(compiled, shots: int, baseline_metrics: dict) -> dict:
    metrics = {**circuit_metrics(compiled), "shots": int(shots)}
    metrics["resource_delta_from_source"] = _resource_delta(metrics, baseline_metrics)
    return metrics


def _strategy_payload(strategy: BenchmarkStrategy, conversion_info: dict) -> dict:
    return {
        "id": strategy.key,
        "label": strategy.label,
        "description": strategy.description,
        "intermediate_representation": strategy.intermediate_representation,
        "compile_profile": strategy.compile_profile,
        "coupling_profile": strategy.coupling_profile,
        "portability_note": strategy.portability_note,
        "qbraid_transform": conversion_info,
    }


def _simulator_result(problem: QAOAProblem, compiled, shots: int, environment: str) -> dict:
    execution = run_transpiled_qaoa(problem, compiled, shots)
    return execution[environment]


def _portable_isa_for_backend(circuit, backend):
    from qiskit import transpile as qiskit_transpile

    portable = _portable_compile(circuit)
    return qiskit_transpile(portable, backend=backend, optimization_level=0)


def _target_aware_isa_for_backend(circuit, backend):
    from qiskit import transpile as qiskit_transpile

    return qiskit_transpile(
        circuit,
        backend=backend,
        optimization_level=2,
        layout_method="sabre",
        routing_method="sabre",
    )


def _run_strategy_on_environment(
    problem: QAOAProblem,
    source_circuit,
    source_metrics: dict,
    strategy: BenchmarkStrategy,
    environment: str,
    shots: int,
    backend=None,
) -> dict:
    normalized_circuit, conversion_info = _qbraid_roundtrip(source_circuit, strategy.intermediate_representation)

    if environment == "ibm_hardware":
        if backend is None:
            raise RuntimeError("IBM backend is required for hardware execution.")
        if strategy.key == PORTABLE_QASM2_STRATEGY.key:
            compiled = _portable_isa_for_backend(normalized_circuit, backend)
        else:
            compiled = _target_aware_isa_for_backend(normalized_circuit, backend)
        output_quality = _ibm_sampler_counts(problem, compiled, shots, backend)
        execution_notes = {
            "execution_environment": "IBM Runtime SamplerV2",
            "target_backend": backend.name,
        }
    else:
        if strategy.key == PORTABLE_QASM2_STRATEGY.key:
            compiled = _portable_compile(normalized_circuit)
        else:
            compiled = _target_aware_compile(normalized_circuit)
        output_quality = _simulator_result(problem, compiled, shots, environment)
        execution_notes = {
            "execution_environment": environment,
            "target_backend": strategy.coupling_profile,
        }

    compiled_metrics = _annotate_metrics(compiled, shots, source_metrics)
    return {
        "strategy": _strategy_payload(strategy, conversion_info),
        "strategy_key": strategy.key,
        "strategy_label": strategy.label,
        "environment": environment,
        "compiled_metrics": compiled_metrics,
        "output_quality": {
            "expected_cost": output_quality["expected_cost"],
            "approximation_ratio": output_quality["approximation_ratio"],
            "success_probability": output_quality["success_probability"],
            "unique_outcomes": output_quality["unique_outcomes"],
        },
        "execution_notes": execution_notes,
        "artifacts": {
            "counts": output_quality.get("counts"),
            "job_id": output_quality.get("job_id"),
            "noise_model": output_quality.get("noise_model"),
            "queue_depth_at_submission": output_quality.get("queue_depth_at_submission"),
        },
    }


def _tradeoff_score(item: dict) -> float:
    quality = float(item["output_quality"]["approximation_ratio"])
    two_qubit_cost = float(item["compiled_metrics"]["two_qubit_gate_count"])
    depth_cost = float(item["compiled_metrics"]["depth"])
    return round(quality - 0.0015 * two_qubit_cost - 0.0002 * depth_cost, 6)


def _environment_priority(environment: str) -> tuple[int, str]:
    order = {"ibm_hardware": 0, "noisy_simulator": 1, "ideal_simulator": 2}
    return (order.get(environment, 99), environment)


def _summarize_environment(results: list[dict]) -> dict:
    quality_winner = max(results, key=lambda item: item["output_quality"]["approximation_ratio"])
    cost_winner = min(results, key=lambda item: item["compiled_metrics"]["two_qubit_gate_count"])
    tradeoff_winner = max(results, key=_tradeoff_score)
    return {
        "quality_winner": {
            "strategy_key": quality_winner["strategy_key"],
            "strategy_label": quality_winner["strategy_label"],
            "approximation_ratio": quality_winner["output_quality"]["approximation_ratio"],
            "success_probability": quality_winner["output_quality"]["success_probability"],
        },
        "cost_winner": {
            "strategy_key": cost_winner["strategy_key"],
            "strategy_label": cost_winner["strategy_label"],
            "two_qubit_gate_count": cost_winner["compiled_metrics"]["two_qubit_gate_count"],
            "depth": cost_winner["compiled_metrics"]["depth"],
        },
        "tradeoff_winner": {
            "strategy_key": tradeoff_winner["strategy_key"],
            "strategy_label": tradeoff_winner["strategy_label"],
            "tradeoff_score": _tradeoff_score(tradeoff_winner),
        },
    }


def _build_conclusion(environment_summary: dict[str, dict]) -> str:
    realistic_environment = sorted(environment_summary.keys(), key=_environment_priority)[0]
    summary = environment_summary[realistic_environment]
    quality = summary["quality_winner"]
    cost = summary["cost_winner"]
    if quality["strategy_key"] == cost["strategy_key"]:
        return (
            f"{quality['strategy_label']} delivered the best quality-cost tradeoff under {realistic_environment}, "
            f"preserving approximation quality while also keeping two-qubit cost lowest."
        )
    return (
        f"{quality['strategy_label']} preserved approximation quality best under {realistic_environment}, "
        f"while {cost['strategy_label']} reduced two-qubit cost more aggressively but at lower output quality."
    )


def _run_real_benchmark(problem: QAOAProblem, candidates: list[dict], shots: int, environments: list[str], availability: dict) -> dict:
    analytical = qaoa_level1(problem)
    exact_bits, exact_cost = brute_force_best(problem)
    worst_bits, worst_cost = brute_force_worst(problem)
    source_circuit = build_qaoa_circuit(problem, analytical["gamma"], analytical["beta"])
    source_metrics = circuit_metrics(source_circuit)
    strategies = [PORTABLE_QASM2_STRATEGY, TARGET_AWARE_QASM3_STRATEGY]
    backend = _select_ibm_backend(source_circuit.num_qubits) if "ibm_hardware" in environments and availability["ibm_execution_ready"] else None

    strategy_results: list[dict] = []
    for strategy in strategies:
        for environment in environments:
            if environment == "ibm_hardware" and backend is None:
                continue
            strategy_results.append(
                _run_strategy_on_environment(
                    problem=problem,
                    source_circuit=source_circuit,
                    source_metrics=source_metrics,
                    strategy=strategy,
                    environment=environment,
                    shots=shots,
                    backend=backend,
                )
            )

    grouped: dict[str, list[dict]] = {}
    for result in strategy_results:
        grouped.setdefault(result["environment"], []).append(result)
    environment_summary = {environment: _summarize_environment(items) for environment, items in grouped.items()}
    best = max(strategy_results, key=_tradeoff_score)
    conclusion = _build_conclusion(environment_summary)

    return {
        "workload": {
            "name": "reduced_subgraph_wildfire_intervention_qaoa",
            "algorithm": "QAOA (p=1)",
            "source_representation": "qiskit.QuantumCircuit",
            "compiler": "qBraid SDK",
            "objective": "Select a reduced set of intervention placements that maximizes disrupted spread potential subject to a planting budget.",
            "wildfire_relevance": "The reduced candidate graph is derived from the wildfire intervention planning module and benchmarks whether the same mitigation workload survives compilation under constrained execution targets.",
            "benchmark_question": "Which qBraid-centered compilation strategy best preserves useful optimization behavior once the reduced intervention workload is compiled for realistic targets?",
            "qiskit_version": _version("qiskit"),
            "qbraid_version": _version("qbraid"),
            "candidate_scope": candidates,
            "problem_size": {
                "num_qubits": source_circuit.num_qubits,
                "num_weights": len(problem.weights),
                "num_pair_penalties": len(problem.pair_penalties),
                "budget": problem.budget,
            },
            "objective_terms": {
                "candidate_weights": problem.weights,
                "pair_penalties": [{"pair": list(pair), "penalty": penalty} for pair, penalty in problem.pair_penalties.items()],
            },
            "uncompiled_circuit": source_metrics,
            "exact_reference": {
                "best_bitstring": list(exact_bits),
                "best_cost": round(float(exact_cost), 4),
                "worst_bitstring": list(worst_bits),
                "worst_cost": round(float(worst_cost), 4),
            },
            "qaoa_reference": analytical,
        },
        "strategies": [
            {
                "id": strategy.key,
                "label": strategy.label,
                "description": strategy.description,
                "intermediate_representation": strategy.intermediate_representation,
                "compile_profile": strategy.compile_profile,
                "coupling_profile": strategy.coupling_profile,
                "basis_gates": list(strategy.basis_gates),
            }
            for strategy in strategies
        ],
        "environments": environments,
        "strategy_results": strategy_results,
        "environment_summary": environment_summary,
        "best_strategy": best["strategy_key"],
        "best_strategy_label": best["strategy_label"],
        "best_environment": best["environment"],
        "conclusion": conclusion,
    }


def create_benchmark_run(
    db: Session,
    scenario: Scenario,
    payload: dict,
    optimization_run: OptimizationRun | None = None,
) -> BenchmarkRun:
    availability = benchmark_availability(payload.get("environments"))
    environment = build_environment(default_environment(scenario))
    candidates, problem = _build_problem(scenario.grid, payload["reduced_candidate_count"], environment)
    exact_bits, exact_cost = brute_force_best(problem)
    worst_bits, worst_cost = brute_force_worst(problem)
    now = datetime.now(timezone.utc)

    if not availability["compiler_aware_benchmarking_ready"]:
        analytical = qaoa_level1(problem)
        run = BenchmarkRun(
            scenario_id=scenario.id,
            optimization_run_id=optimization_run.id if optimization_run else None,
            scenario_version=scenario.version,
            status="degraded",
            request_json=payload,
            results_json={
                "workload": {
                    "name": "reduced_subgraph_wildfire_intervention_qaoa",
                    "algorithm": "QAOA (p=1)",
                    "source_representation": "qiskit.QuantumCircuit",
                    "objective": "Select intervention placements that disrupt wildfire spread potential under a budget constraint.",
                    "candidate_scope": candidates,
                    "exact_reference": {
                        "best_bitstring": list(exact_bits),
                        "best_cost": round(float(exact_cost), 4),
                        "worst_bitstring": list(worst_bits),
                        "worst_cost": round(float(worst_cost), 4),
                    },
                    "qaoa_reference": analytical,
                },
                "note": availability["reason"],
            },
            summary_json={
                "generated_at": now.isoformat(),
                "recommendation": "Compiler-aware benchmark unavailable in current environment.",
                "status_detail": availability["reason"],
            },
            availability_json=availability,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    requested_environments = payload["environments"]
    executed_environments = list(requested_environments)
    if "ibm_hardware" in requested_environments and not availability["ibm_execution_ready"]:
        executed_environments = [env for env in requested_environments if env != "ibm_hardware"]

    benchmark_data = _run_real_benchmark(problem, candidates, payload["shots"], executed_environments, availability)
    best = next(
        item
        for item in benchmark_data["strategy_results"]
        if item["strategy_key"] == benchmark_data["best_strategy"] and item["environment"] == benchmark_data["best_environment"]
    )
    run = BenchmarkRun(
        scenario_id=scenario.id,
        optimization_run_id=optimization_run.id if optimization_run else None,
        scenario_version=scenario.version,
        status="complete",
        request_json={**payload, "environments": executed_environments},
        results_json={
            **benchmark_data,
            "requested_environments": requested_environments,
            "executed_environments": executed_environments,
        },
        summary_json={
            "generated_at": now.isoformat(),
            "recommendation": benchmark_data["conclusion"],
            "best_strategy": benchmark_data["best_strategy"],
            "best_strategy_label": benchmark_data["best_strategy_label"],
            "best_environment": benchmark_data["best_environment"],
            "best_approximation_ratio": best["output_quality"]["approximation_ratio"],
            "best_success_probability": best["output_quality"]["success_probability"],
            "best_depth": best["compiled_metrics"]["depth"],
            "best_two_qubit_gate_count": best["compiled_metrics"]["two_qubit_gate_count"],
            "best_total_gates": best["compiled_metrics"]["total_gates"],
            "qiskit_version": _version("qiskit"),
            "qbraid_version": _version("qbraid"),
            "circuit_type": "qiskit.quantumcircuit",
            "source_representation": "qiskit.QuantumCircuit",
            "algorithm": "QAOA (p=1)",
        },
        availability_json=availability,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
