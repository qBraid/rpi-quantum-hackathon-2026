from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from time import time
from typing import Any, Callable

import numpy as np
import rustworkx as rx
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import efficient_su2
from qiskit.quantum_info import SparsePauliOp

from problems.base import ParameterEvaluator, Problem


@dataclass(frozen=True)
class MaxCutProblemData:
    graph: Any
    pce_x: list[SparsePauliOp]
    pce_y: list[SparsePauliOp]
    pce_z: list[SparsePauliOp]
    setup_time: float
    seed: int


@dataclass(frozen=True)
class MaxCutProblem(Problem):
    num_nodes: int
    num_qubits: int
    graph_probability: float
    seed: int
    reps: int

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
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

    @classmethod
    def from_namespace(cls, args) -> MaxCutProblem:
        return cls(
            num_nodes=args.num_nodes,
            num_qubits=args.num_qubits,
            graph_probability=args.graph_probability,
            seed=args.seed,
            reps=args.reps,
        )

    @staticmethod
    def _calc_cut_size(graph, partition0, partition1):
        cut_size = 0
        for edge0, edge1 in graph.edge_list():
            if edge0 in partition0 and edge1 in partition1:
                cut_size += 1
            elif edge0 in partition1 and edge1 in partition0:
                cut_size += 1
        return cut_size

    @staticmethod
    def _build_pauli_correlation_encoding(
        pauli: str, node_list: list[int], n: int, k: int = 2
    ) -> list[SparsePauliOp]:
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

    def build_problem_data(self) -> MaxCutProblemData:
        print("Creating MaxCut problem with Pauli Correlation Encoding...")
        start_problem = time()

        graph = rx.undirected_gnp_random_graph(
            self.num_nodes, self.graph_probability, seed=self.seed
        )
        print(f"Graph: {self.num_nodes} nodes, {len(graph.edges())} edges")

        list_size = self.num_nodes // 3
        node_x = [i for i in range(list_size)]
        node_y = [i for i in range(list_size, 2 * list_size)]
        node_z = [i for i in range(2 * list_size, self.num_nodes)]

        pce_x = self._build_pauli_correlation_encoding("X", node_x, self.num_qubits)
        pce_y = self._build_pauli_correlation_encoding("Y", node_y, self.num_qubits)
        pce_z = self._build_pauli_correlation_encoding("Z", node_z, self.num_qubits)

        setup_time = time() - start_problem
        print(f"✓ Problem setup completed in {setup_time:.4f}s\n")

        return MaxCutProblemData(
            graph=graph,
            pce_x=pce_x,
            pce_y=pce_y,
            pce_z=pce_z,
            setup_time=setup_time,
            seed=self.seed,
        )

    def build_ansatz(self) -> QuantumCircuit:
        print("Building quantum circuit...")
        qc = efficient_su2(self.num_qubits, ["ry", "rz"], reps=self.reps)
        print(
            f"Circuit: {self.num_qubits} qubits, {qc.num_parameters} parameters, depth {qc.depth()}"
        )
        return qc

    def build_observables(self, layout: Any, problem_data: Any) -> list[list[SparsePauliOp]]:
        if layout is None:
            return [
                list(problem_data.pce_x),
                list(problem_data.pce_y),
                list(problem_data.pce_z),
            ]

        return [
            [op.apply_layout(layout) for op in problem_data.pce_x],
            [op.apply_layout(layout) for op in problem_data.pce_y],
            [op.apply_layout(layout) for op in problem_data.pce_z],
        ]

    def make_loss(
        self,
        *,
        problem_data: Any,
        evaluator: ParameterEvaluator,
        experiment_results: list[dict[str, Any]],
        iteration_times: list[float],
    ) -> Callable[[np.ndarray], float]:
        def loss_func_estimator(x: np.ndarray) -> float:
            iter_start = time()
            params = np.asarray(x, dtype=float)
            node_exp_map = evaluator(params)

            alpha = self.num_qubits
            loss = 0.0
            for edge0, edge1 in problem_data.graph.edge_list():
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
            v = len(problem_data.graph.edges()) / 2 + (len(problem_data.graph.nodes()) - 1) / 4
            regulation_term = beta * v * regulation_term

            loss = loss + regulation_term

            iter_time = time() - iter_start
            iteration_times.append(iter_time)
            print(
                f"  Iteration {len(experiment_results):3d} | Loss: {loss:10.6f} | Time: {iter_time:.4f}s"
            )
            experiment_results.append({"loss": loss, "exp_map": node_exp_map})
            return loss

        return loss_func_estimator

    def postprocess(
        self, *, problem_data: Any, experiment_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not experiment_results:
            raise RuntimeError("Optimization completed without producing any iterations.")

        final_exp_map = experiment_results[-1]["exp_map"]
        par0, par1 = set(), set()
        for i in final_exp_map:
            if final_exp_map[i] >= 0:
                par0.add(i)
            else:
                par1.add(i)

        cut_size = self._calc_cut_size(problem_data.graph, par0, par1)
        return {
            "cut_size": cut_size,
            "partition0": sorted(par0),
            "partition1": sorted(par1),
            "exp_map": final_exp_map,
        }

