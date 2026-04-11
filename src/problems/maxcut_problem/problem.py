from dataclasses import dataclass
import logging
from time import time
from typing import Any, Callable, Self

import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import efficient_su2

from problems.base import ParameterEvaluator, Problem

from .model import MaxCutModel, MaxCutProblemData


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
    def from_namespace(cls, args) -> Self:
        return cls(
            num_nodes=args.num_nodes,
            num_qubits=args.num_qubits,
            graph_probability=args.graph_probability,
            seed=args.seed,
            reps=args.reps,
        )

    def build_problem_data(self, *, logger: logging.Logger) -> MaxCutProblemData:
        return MaxCutModel.build_problem_data(
            num_nodes=self.num_nodes,
            num_qubits=self.num_qubits,
            graph_probability=self.graph_probability,
            seed=self.seed,
            logger=logger,
        )

    def build_ansatz(self, *, logger: logging.Logger) -> QuantumCircuit:
        logger.info("Building quantum circuit")
        qc = efficient_su2(self.num_qubits, ["ry", "rz"], reps=self.reps)
        logger.info(
            "Circuit qubits=%s params=%s depth=%s",
            self.num_qubits,
            qc.num_parameters,
            qc.depth(),
        )
        return qc

    def build_observables(self, layout: Any, problem_data: Any) -> list[list[Any]]:
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

    def metric_candidates(self) -> tuple[str, ...]:
        return ("cut_size",)

    def make_loss(
        self,
        *,
        problem_data: Any,
        evaluator: ParameterEvaluator,
        experiment_results: list[dict[str, Any]],
        iteration_times: list[float],
        logger: logging.Logger,
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
            logger.info(
                "Iteration %3d loss=%10.6f time=%.4fs",
                len(experiment_results),
                loss,
                iter_time,
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
        par0, par1 = MaxCutModel.build_partitions(final_exp_map)
        cut_size = MaxCutModel.calc_cut_size(problem_data.graph, par0, par1)
        return {
            "cut_size": cut_size,
            "partition0": sorted(par0),
            "partition1": sorted(par1),
            "exp_map": final_exp_map,
        }

