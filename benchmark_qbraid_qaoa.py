"""Compiler-aware quantum benchmark using qBraid + QAOA MaxCut.

This script builds a QAOA workload in Qiskit, compiles it with two qBraid
transpilation strategies, and compares quality-vs-cost tradeoffs under two
execution environments:
1) Ideal simulator
2) Noisy, constrained simulator
"""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx
import numpy as np
from qbraid import ConversionGraph, ConversionScheme, transpile
from qiskit import QuantumCircuit, transpile as qiskit_transpile
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error


@dataclass
class StrategyResult:
    name: str
    qbraid_target: str
    depth: int
    two_qubit_count: int
    width: int
    ideal_success_prob: float
    ideal_approx_ratio: float
    noisy_success_prob: float
    noisy_approx_ratio: float


def build_graph() -> nx.Graph:
    """Small weighted MaxCut instance for QAOA benchmarking."""
    g = nx.Graph()
    # 4-node cycle with a chord to make objective nontrivial.
    weighted_edges = [
        (0, 1, 1.0),
        (1, 2, 1.0),
        (2, 3, 1.0),
        (3, 0, 1.0),
        (0, 2, 0.5),
    ]
    g.add_weighted_edges_from(weighted_edges)
    return g


def bitstring_cut_value(bitstring: str, graph: nx.Graph) -> float:
    value = 0.0
    # Qiskit bitstring ordering is little-endian by default in counts keys.
    bits = bitstring[::-1]
    for u, v, data in graph.edges(data=True):
        if bits[u] != bits[v]:
            value += float(data.get("weight", 1.0))
    return value


def exact_maxcut_value(graph: nx.Graph) -> float:
    n = graph.number_of_nodes()
    best = 0.0
    for assignment in itertools.product(["0", "1"], repeat=n):
        candidate = "".join(assignment)
        best = max(best, bitstring_cut_value(candidate, graph))
    return best


def build_qaoa_circuit(graph: nx.Graph, gamma: float, beta: float) -> QuantumCircuit:
    n = graph.number_of_nodes()
    qc = QuantumCircuit(n, n)

    # Uniform superposition.
    for q in range(n):
        qc.h(q)

    # Cost unitary for MaxCut (p=1 layer).
    for u, v, data in graph.edges(data=True):
        w = float(data.get("weight", 1.0))
        qc.cx(u, v)
        qc.rz(2.0 * gamma * w, v)
        qc.cx(u, v)

    # Mixer unitary.
    for q in range(n):
        qc.rx(2.0 * beta, q)

    qc.measure(range(n), range(n))
    return qc


def approximation_ratio_from_counts(
    counts: Dict[str, int], graph: nx.Graph, optimum: float
) -> Tuple[float, float]:
    shots = sum(counts.values())
    if shots == 0:
        return 0.0, 0.0

    expected = 0.0
    opt_hits = 0
    for bitstring, c in counts.items():
        val = bitstring_cut_value(bitstring, graph)
        expected += val * c
        if np.isclose(val, optimum):
            opt_hits += c

    approx_ratio = (expected / shots) / optimum
    success_prob = opt_hits / shots
    return success_prob, approx_ratio


def build_noise_model() -> NoiseModel:
    noise = NoiseModel()

    one_q_error = depolarizing_error(0.001, 1)
    two_q_error = depolarizing_error(0.02, 2)
    readout = ReadoutError([[0.97, 0.03], [0.04, 0.96]])

    for gate in ["x", "sx", "rz", "rx"]:
        noise.add_all_qubit_quantum_error(one_q_error, gate)
    noise.add_all_qubit_quantum_error(two_q_error, "cx")
    noise.add_all_qubit_readout_error(readout)

    return noise


def run_counts_ideal(qc: QuantumCircuit, shots: int) -> Dict[str, int]:
    qc = ensure_single_qiskit_circuit(qc)
    sim = AerSimulator()
    tqc = qiskit_transpile(qc, sim, optimization_level=1)
    result = sim.run(tqc, shots=shots).result()
    return result.get_counts()


def run_counts_noisy_constrained(qc: QuantumCircuit, shots: int) -> Dict[str, int]:
    qc = ensure_single_qiskit_circuit(qc)
    # Simple linear connectivity and restricted basis to emulate hardware limits.
    coupling_map = CouplingMap(couplinglist=[(0, 1), (1, 2), (2, 3)])
    basis_gates = ["rz", "sx", "x", "rx", "cx"]
    noise_model = build_noise_model()

    sim = AerSimulator(noise_model=noise_model)
    tqc = qiskit_transpile(
        qc,
        sim,
        basis_gates=basis_gates,
        coupling_map=coupling_map,
        optimization_level=3,
    )
    result = sim.run(tqc, shots=shots).result()
    return result.get_counts()


def ensure_single_qiskit_circuit(obj) -> QuantumCircuit:
    """Normalize qiskit program container outputs into one QuantumCircuit."""
    if isinstance(obj, QuantumCircuit):
        return obj

    if isinstance(obj, (list, tuple)) and obj and isinstance(obj[0], QuantumCircuit):
        return obj[0]

    raise TypeError(f"Expected QuantumCircuit or non-empty circuit list, got {type(obj)}")


def to_qiskit_for_execution(qprogram_obj, strategy_name: str) -> QuantumCircuit:
    """Ensure execution circuits are in Qiskit after qBraid compilation."""
    try:
        converted = transpile(qprogram_obj, "qiskit")
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise RuntimeError(
            f"Failed to convert strategy '{strategy_name}' output back to qiskit: {exc}"
        ) from exc

    return ensure_single_qiskit_circuit(converted)


def compile_strategies(source_qiskit: QuantumCircuit) -> List[Tuple[str, str, QuantumCircuit]]:
    """Produce two compiled variants using different qBraid strategies."""
    graph = ConversionGraph()

    scheme_a = ConversionScheme(
        conversion_graph=graph,
        max_path_attempts=2,
        max_path_depth=2,
    )

    scheme_b = ConversionScheme(
        conversion_graph=graph,
        max_path_attempts=6,
        max_path_depth=None,
    )

    # Strategy A: constrained path search, target OpenQASM2.
    qasm2_prog = transpile(
        source_qiskit,
        "qasm2",
        conversion_graph=scheme_a.conversion_graph,
        max_path_attempts=scheme_a.max_path_attempts,
        max_path_depth=scheme_a.max_path_depth,
    )
    strat_a_qiskit = to_qiskit_for_execution(qasm2_prog, "A_qasm2_constrained")

    # Strategy B: more permissive path search, target OpenQASM3.
    qasm3_prog = transpile(
        source_qiskit,
        "qasm3",
        conversion_graph=scheme_b.conversion_graph,
        max_path_attempts=scheme_b.max_path_attempts,
        max_path_depth=scheme_b.max_path_depth,
    )
    strat_b_qiskit = to_qiskit_for_execution(qasm3_prog, "B_qasm3_flexible")

    return [
        ("A_qasm2_constrained", "qasm2", strat_a_qiskit),
        ("B_qasm3_flexible", "qasm3", strat_b_qiskit),
    ]


def benchmark(shots: int, grid_points: int) -> Dict[str, object]:
    graph = build_graph()
    optimum = exact_maxcut_value(graph)

    # Light-weight parameter sweep to make this a real algorithmic workflow.
    gammas = np.linspace(0.1, np.pi - 0.1, grid_points)
    betas = np.linspace(0.1, np.pi / 2 - 0.1, grid_points)

    best_gamma = None
    best_beta = None
    best_ratio = -1.0

    for gamma in gammas:
        for beta in betas:
            trial = build_qaoa_circuit(graph, float(gamma), float(beta))
            counts = run_counts_ideal(trial, shots=max(256, shots // 4))
            _, ratio = approximation_ratio_from_counts(counts, graph, optimum)
            if ratio > best_ratio:
                best_ratio = ratio
                best_gamma = float(gamma)
                best_beta = float(beta)

    source = build_qaoa_circuit(graph, best_gamma, best_beta)
    strategies = compile_strategies(source)

    results: List[StrategyResult] = []

    for strategy_name, target_name, compiled_qiskit in strategies:
        # Resource metrics are measured from compiled artifact used for execution.
        depth = compiled_qiskit.depth()
        ops = compiled_qiskit.count_ops()
        twoq = int(ops.get("cx", 0) + ops.get("cz", 0) + ops.get("ecr", 0))
        width = compiled_qiskit.num_qubits

        ideal_counts = run_counts_ideal(compiled_qiskit, shots=shots)
        noisy_counts = run_counts_noisy_constrained(compiled_qiskit, shots=shots)

        ideal_success, ideal_ratio = approximation_ratio_from_counts(
            ideal_counts, graph, optimum
        )
        noisy_success, noisy_ratio = approximation_ratio_from_counts(
            noisy_counts, graph, optimum
        )

        results.append(
            StrategyResult(
                name=strategy_name,
                qbraid_target=target_name,
                depth=depth,
                two_qubit_count=twoq,
                width=width,
                ideal_success_prob=ideal_success,
                ideal_approx_ratio=ideal_ratio,
                noisy_success_prob=noisy_success,
                noisy_approx_ratio=noisy_ratio,
            )
        )

    # Select best quality/cost tradeoff using noisy approximation ratio per 2Q gate.
    scored = []
    for row in results:
        denom = max(row.two_qubit_count, 1)
        tradeoff = row.noisy_approx_ratio / denom
        scored.append((tradeoff, row.name))
    scored.sort(reverse=True)

    return {
        "algorithm": "QAOA MaxCut (p=1)",
        "source_framework": "qiskit",
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges(),
        "maxcut_optimum": optimum,
        "selected_parameters": {"gamma": best_gamma, "beta": best_beta},
        "strategy_results": [row.__dict__ for row in results],
        "best_tradeoff_strategy": scored[0][1],
        "tradeoff_definition": "noisy_approx_ratio / max(two_qubit_count,1)",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="qBraid compiler-aware QAOA benchmark")
    parser.add_argument("--shots", type=int, default=2048, help="Shots per experiment")
    parser.add_argument(
        "--grid-points",
        type=int,
        default=6,
        help="Grid points per QAOA parameter axis for coarse tuning",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/benchmark_results.json",
        help="Where to write JSON benchmark output",
    )
    args = parser.parse_args()

    report = benchmark(shots=args.shots, grid_points=args.grid_points)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=== qBraid Compiler-Aware Benchmark Complete ===")
    print(json.dumps(report, indent=2))
    print(f"Saved results to: {out_path}")


if __name__ == "__main__":
    main()
