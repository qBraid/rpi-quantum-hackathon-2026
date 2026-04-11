from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import time
from typing import Any, Callable

import matplotlib.pyplot as plt
import numpy as np
import rustworkx as rx
from dotenv import load_dotenv
from scipy.optimize import minimize

from qiskit_aer import AerSimulator
from qiskit.circuit.library import efficient_su2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime import QiskitRuntimeService


@dataclass(frozen=True)
class AppConfig:
    mode: str
    backend_name: str
    num_nodes: int
    num_qubits: int
    graph_probability: float
    maxiter: int
    seed: int
    reps: int


@dataclass(frozen=True)
class RuntimeBundle:
    label: str
    transpile_backend: Any
    estimator_mode: Any
    parameter_transform: Callable[[np.ndarray], np.ndarray]


def calc_cut_size(graph, partition0, partition1):
    """Calculate the cut size of the given partitions of the graph."""
    cut_size = 0
    for edge0, edge1 in graph.edge_list():
        if edge0 in partition0 and edge1 in partition1:
            cut_size += 1
        elif edge0 in partition1 and edge1 in partition0:
            cut_size += 1
    return cut_size


def build_pauli_correlation_encoding(pauli, node_list, n, k=2):
    """Build Pauli correlation encoding for the given Pauli label and node list."""
    pauli_correlation_encoding = []
    for idx, c in enumerate(combinations(range(n), k)):
        if idx >= len(node_list):
            break
        paulis = ["I"] * n
        paulis[c[0]], paulis[c[1]] = pauli, pauli
        pauli_correlation_encoding.append(("".join(paulis)[::-1], 1))

    hamiltonian = []
    for pauli_label, weight in pauli_correlation_encoding:
        hamiltonian.append(SparsePauliOp.from_list([(pauli_label, weight)]))

    return hamiltonian


def snap_to_clifford_angles(params: np.ndarray) -> np.ndarray:
    """Project parameters onto Clifford-compatible multiples of pi/2."""
    params = np.asarray(params, dtype=float)
    step = np.pi / 2
    return np.round(params / step) * step


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the MaxCut benchmark on IBM hardware, an Aer simulator seeded "
            "from hardware, or a Clifford stabilizer simulator."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("hardware", "aer", "clifford"),
        default="aer",
        help="Choose the execution mode.",
    )
    parser.add_argument(
        "--backend",
        default="ibm_rensselaer",
        help="IBM backend name to use for hardware and Aer-from-hardware modes.",
    )
    parser.add_argument(
        "--num-nodes",
        type=int,
        default=100,
        help="Number of graph nodes to generate.",
    )
    parser.add_argument(
        "--num-qubits",
        type=int,
        default=10,
        help="Number of qubits in the ansatz.",
    )
    parser.add_argument(
        "--graph-probability",
        type=float,
        default=0.1,
        help="Edge probability for the random graph.",
    )
    parser.add_argument(
        "--maxiter",
        type=int,
        default=10,
        help="Maximum number of COBYLA iterations.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used for graph and parameter initialization.",
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=2,
        help="Number of repetitions in the ansatz circuit.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> AppConfig:
    args = build_parser().parse_args(argv)
    return AppConfig(
        mode=args.mode,
        backend_name=args.backend,
        num_nodes=args.num_nodes,
        num_qubits=args.num_qubits,
        graph_probability=args.graph_probability,
        maxiter=args.maxiter,
        seed=args.seed,
        reps=args.reps,
    )


def build_runtime(config: AppConfig) -> RuntimeBundle:
    """Create the runtime objects for the requested execution mode."""
    if config.mode in {"hardware", "aer"}:
        load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
        try:
            service = QiskitRuntimeService()
        except Exception as exc:  # pragma: no cover - runtime environment dependent
            raise RuntimeError(
                "IBM Runtime service initialization failed. Set up your IBM Quantum "
                "credentials before using hardware or Aer-from-hardware mode."
            ) from exc

        backend = service.backend(config.backend_name)
        if config.mode == "hardware":
            return RuntimeBundle(
                label=f"IBM hardware backend '{config.backend_name}'",
                transpile_backend=backend,
                estimator_mode=backend,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
            )

        simulator = AerSimulator.from_backend(backend)
        return RuntimeBundle(
            label=f"Aer simulator seeded from '{config.backend_name}'",
            transpile_backend=simulator,
            estimator_mode=simulator,
            parameter_transform=lambda params: np.asarray(params, dtype=float),
        )

    simulator = AerSimulator(method="stabilizer")  # type: ignore[arg-type]
    return RuntimeBundle(
        label="Clifford stabilizer simulation",
        transpile_backend=simulator,
        estimator_mode=simulator,
        parameter_transform=snap_to_clifford_angles,
    )


def build_problem(config: AppConfig):
    print("Creating MaxCut problem with Pauli Correlation Encoding...")
    start_problem = time.time()

    graph = rx.undirected_gnp_random_graph(
        config.num_nodes, config.graph_probability, seed=config.seed
    )
    print(f"Graph: {config.num_nodes} nodes, {len(graph.edges())} edges")

    list_size = config.num_nodes // 3
    node_x = [i for i in range(list_size)]
    node_y = [i for i in range(list_size, 2 * list_size)]
    node_z = [i for i in range(2 * list_size, config.num_nodes)]

    pauli_correlation_encoding_x = build_pauli_correlation_encoding(
        "X", node_x, config.num_qubits
    )
    pauli_correlation_encoding_y = build_pauli_correlation_encoding(
        "Y", node_y, config.num_qubits
    )
    pauli_correlation_encoding_z = build_pauli_correlation_encoding(
        "Z", node_z, config.num_qubits
    )

    problem_setup_time = time.time() - start_problem
    print(f"✓ Problem setup completed in {problem_setup_time:.4f}s\n")

    return (
        graph,
        pauli_correlation_encoding_x,
        pauli_correlation_encoding_y,
        pauli_correlation_encoding_z,
        problem_setup_time,
    )


def build_circuit(config: AppConfig, runtime: RuntimeBundle):
    print("Building and optimizing quantum circuit...")
    start_circuit = time.time()

    qc = efficient_su2(config.num_qubits, ["ry", "rz"], reps=config.reps)
    print(
        f"Circuit: {config.num_qubits} qubits, {qc.num_parameters} parameters, depth {qc.depth()}"
    )

    pm = generate_preset_pass_manager(
        backend=runtime.transpile_backend, optimization_level=3
    )
    qc_optimized = pm.run(qc)
    print(f"Optimized circuit depth: {qc_optimized.depth()}")

    circuit_time = time.time() - start_circuit
    print(f"✓ Circuit optimization completed in {circuit_time:.4f}s\n")

    return qc_optimized, circuit_time


def make_loss_function(
    *,
    config: AppConfig,
    graph,
    ansatz,
    hamiltonians,
    estimator,
    runtime: RuntimeBundle,
    experiment_results: list[dict],
    iteration_times: list[float],
):
    def loss_func_estimator(x):
        iter_start = time.time()
        params = runtime.parameter_transform(np.asarray(x, dtype=float))

        job = estimator.run(
            [
                (ansatz, hamiltonians[0], params),
                (ansatz, hamiltonians[1], params),
                (ansatz, hamiltonians[2], params),
            ]
        )
        result = job.result()

        node_exp_map = {}
        idx = 0
        for r in result:
            for ev in r.data.evs:
                node_exp_map[idx] = ev
                idx += 1

        alpha = config.num_qubits
        loss = 0.0
        for edge0, edge1 in graph.edge_list():
            if edge0 < len(node_exp_map) and edge1 < len(node_exp_map):
                loss += np.tanh(alpha * node_exp_map[edge0]) * np.tanh(
                    alpha * node_exp_map[edge1]
                )

        regulation_term = 0.0
        for i in range(len(node_exp_map)):
            regulation_term += np.tanh(alpha * node_exp_map[i]) ** 2
        regulation_term = regulation_term / max(len(node_exp_map), 1)
        regulation_term = regulation_term**2
        beta = 1 / 2
        v = len(graph.edges()) / 2 + (len(graph.nodes()) - 1) / 4
        regulation_term = beta * v * regulation_term

        loss = loss + regulation_term

        iter_time = time.time() - iter_start
        iteration_times.append(iter_time)

        print(
            f"  Iteration {len(experiment_results):3d} | Loss: {loss:10.6f} | Time: {iter_time:.4f}s"
        )
        experiment_results.append({"loss": loss, "exp_map": node_exp_map})
        return loss

    return loss_func_estimator


def run_pipeline(config: AppConfig):
    print(f"Selected mode: {config.mode}")
    start_setup = time.time()
    runtime = build_runtime(config)
    setup_time = time.time() - start_setup
    print(f"✓ Runtime setup completed in {setup_time:.4f}s ({runtime.label})\n")

    graph, pce_x, pce_y, pce_z, problem_setup_time = build_problem(config)
    qc_optimized, circuit_time = build_circuit(config, runtime)

    print(f"Starting optimization on {runtime.label}...")
    start_optimization = time.time()

    pce = [
        [op.apply_layout(qc_optimized.layout) for op in pce_x],
        [op.apply_layout(qc_optimized.layout) for op in pce_y],
        [op.apply_layout(qc_optimized.layout) for op in pce_z],
    ]

    estimator = Estimator(mode=runtime.estimator_mode)
    experiment_results: list[dict] = []
    iteration_times: list[float] = []
    loss_func = make_loss_function(
        config=config,
        graph=graph,
        ansatz=qc_optimized,
        hamiltonians=pce,
        estimator=estimator,
        runtime=runtime,
        experiment_results=experiment_results,
        iteration_times=iteration_times,
    )

    np.random.seed(config.seed)
    initial_params = np.random.rand(qc_optimized.num_parameters)

    cobyla_miniter = qc_optimized.num_parameters + 2
    cobyla_maxiter = max(config.maxiter, cobyla_miniter)
    if cobyla_maxiter != config.maxiter:
        print(
            f"Requested COBYLA maxiter={config.maxiter} is below the solver minimum "
            f"for {qc_optimized.num_parameters} parameters; using {cobyla_maxiter} instead."
        )

    minimize_options: dict[str, int] = {"maxiter": cobyla_maxiter}
    result = minimize(
        loss_func,
        initial_params,
        method="COBYLA",
        options=minimize_options,
    )  # type: ignore[arg-type]

    optimization_time = time.time() - start_optimization
    print(f"\n✓ Optimization completed in {optimization_time:.4f}s\n")

    if not experiment_results:
        raise RuntimeError("Optimization completed without producing any iterations.")

    print("Processing results...")
    par0, par1 = set(), set()
    for i in experiment_results[-1]["exp_map"]:
        if experiment_results[-1]["exp_map"][i] >= 0:
            par0.add(i)
        else:
            par1.add(i)

    cut_size = calc_cut_size(graph, par0, par1)
    print(f"Final cut size: {cut_size}")
    print(f"Optimization result:\n{result}\n")

    print("=" * 70)
    print("BENCHMARKING SUMMARY")
    print("=" * 70)
    print(f"Setup time (runtime creation):         {setup_time:10.4f}s")
    print(f"Problem setup time:                    {problem_setup_time:10.4f}s")
    print(f"Circuit setup & optimization time:     {circuit_time:10.4f}s")
    print(f"Optimization loop time:                {optimization_time:10.4f}s")
    print(f"  - Average time per iteration:        {np.mean(iteration_times):10.4f}s")
    print(f"  - Min iteration time:                {np.min(iteration_times):10.4f}s")
    print(f"  - Max iteration time:                {np.max(iteration_times):10.4f}s")
    print(
        f"Total runtime:                         {setup_time + problem_setup_time + circuit_time + optimization_time:10.4f}s"
    )
    print("=" * 70)

    plt.show()


def main(argv: list[str] | None = None):
    config = parse_args(argv)
    run_pipeline(config)


if __name__ == "__main__":
    main()


