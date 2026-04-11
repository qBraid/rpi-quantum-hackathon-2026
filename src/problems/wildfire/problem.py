from dataclasses import dataclass
import logging
from time import time
from typing import Any, Callable, Self

import numpy as np
from qiskit.circuit import ParameterVector, QuantumCircuit

from problems.base import ParameterEvaluator, Problem

from .model import WildfireModel, WildfireProblemData


def _build_grid_quantum_circuit(
    gamma: list[Any],
    beta: list[Any],
    max_active: int = 10,
    grid_size: tuple[int, int] = (10, 10),
) -> QuantumCircuit:
    num_qubits = grid_size[0] * grid_size[1]
    qc = QuantumCircuit(num_qubits)
    qc.x(range(max_active))

    for gamma_i, beta_i in zip(gamma, beta):
        vertical_odd = QuantumCircuit(num_qubits)
        vertical_even = QuantumCircuit(num_qubits)

        vertical_odd.rz(0 - gamma_i, range(num_qubits))
        vertical_even.rz(0 - gamma_i, range(num_qubits))

        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                if j % 2 == 0:
                    vertical_odd.cx(idx, idx + 1)
                    vertical_odd.rz(gamma_i, idx + 1)
                    vertical_odd.cx(idx, idx + 1)
                else:
                    vertical_even.cx(idx, idx + 1)
                    vertical_even.rz(gamma_i, idx + 1)
                    vertical_even.cx(idx, idx + 1)

        qc.compose(vertical_odd, inplace=True)
        qc.barrier()
        qc.compose(vertical_even, inplace=True)
        qc.barrier()

        horizontal_odd = QuantumCircuit(num_qubits)
        horizontal_even = QuantumCircuit(num_qubits)
        horizontal_odd.rz(0 - gamma_i, range(num_qubits))
        horizontal_even.rz(0 - gamma_i, range(num_qubits))
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                if i % 2 == 0:
                    horizontal_odd.cx(idx, idx + grid_size[1])
                    horizontal_odd.rz(gamma_i, idx + grid_size[1])
                    horizontal_odd.cx(idx, idx + grid_size[1])
                else:
                    horizontal_even.cx(idx, idx + grid_size[1])
                    horizontal_even.rz(gamma_i, idx + grid_size[1])
                    horizontal_even.cx(idx, idx + grid_size[1])

        qc.compose(horizontal_odd, inplace=True)
        qc.barrier()
        qc.compose(horizontal_even, inplace=True)
        qc.barrier()

        qc.h(range(num_qubits))

        vertical_odd = QuantumCircuit(num_qubits)
        vertical_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                if j % 2 == 0:
                    vertical_odd.cx(idx, idx + 1)
                    vertical_odd.rz(2 * beta_i, idx + 1)
                    vertical_odd.cx(idx, idx + 1)
                else:
                    vertical_even.cx(idx, idx + 1)
                    vertical_even.rz(2 * beta_i, idx + 1)
                    vertical_even.cx(idx, idx + 1)

        qc.compose(vertical_odd, inplace=True)
        qc.barrier()
        qc.compose(vertical_even, inplace=True)
        qc.barrier()

        horizontal_odd = QuantumCircuit(num_qubits)
        horizontal_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                if i % 2 == 0:
                    horizontal_odd.cx(idx, idx + grid_size[1])
                    horizontal_odd.rz(2 * beta_i, idx + grid_size[1])
                    horizontal_odd.cx(idx, idx + grid_size[1])
                else:
                    horizontal_even.cx(idx, idx + grid_size[1])
                    horizontal_even.rz(2 * beta_i, idx + grid_size[1])
                    horizontal_even.cx(idx, idx + grid_size[1])

        qc.compose(horizontal_odd, inplace=True)
        qc.barrier()
        qc.compose(horizontal_even, inplace=True)
        qc.barrier()

        qc.h(range(num_qubits))
        qc.s(range(num_qubits))
        qc.h(range(num_qubits))

        vertical_odd = QuantumCircuit(num_qubits)
        vertical_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0]):
            for j in range(grid_size[1] - 1):
                idx = i * grid_size[1] + j

                if j % 2 == 0:
                    vertical_odd.cx(idx, idx + 1)
                    vertical_odd.rz(2 * beta_i, idx + 1)
                    vertical_odd.cx(idx, idx + 1)
                else:
                    vertical_even.cx(idx, idx + 1)
                    vertical_even.rz(2 * beta_i, idx + 1)
                    vertical_even.cx(idx, idx + 1)

        qc.compose(vertical_odd, inplace=True)
        qc.barrier()
        qc.compose(vertical_even, inplace=True)
        qc.barrier()

        horizontal_odd = QuantumCircuit(num_qubits)
        horizontal_even = QuantumCircuit(num_qubits)
        for i in range(grid_size[0] - 1):
            for j in range(grid_size[1]):
                idx = i * grid_size[1] + j

                if i % 2 == 0:
                    horizontal_odd.cx(idx, idx + grid_size[1])
                    horizontal_odd.rz(2 * beta_i, idx + grid_size[1])
                    horizontal_odd.cx(idx, idx + grid_size[1])
                else:
                    horizontal_even.cx(idx, idx + grid_size[1])
                    horizontal_even.rz(2 * beta_i, idx + grid_size[1])
                    horizontal_even.cx(idx, idx + grid_size[1])

        qc.compose(horizontal_odd, inplace=True)
        qc.barrier()
        qc.compose(horizontal_even, inplace=True)
        qc.barrier()

        qc.h(range(num_qubits))
        qc.sdg(range(num_qubits))

    return qc


@dataclass(frozen=True)
class WildfireMitigationProblem(Problem):
    grid_rows: int
    grid_cols: int
    shrub_budget: int
    brush_probability: float
    seed: int
    reps: int

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        parser.add_argument(
            "--grid-rows",
            type=int,
            default=10,
            help="Number of rows in the wildfire mitigation grid.",
        )
        parser.add_argument(
            "--grid-cols",
            type=int,
            default=10,
            help="Number of columns in the wildfire mitigation grid.",
        )
        parser.add_argument(
            "--shrub-budget",
            type=int,
            default=10,
            help="Number of Toyon shrubs available for planting.",
        )
        parser.add_argument(
            "--brush-probability",
            type=float,
            default=0.7,
            help="Probability that a grid cell is highly flammable dry brush.",
        )
        parser.add_argument(
            "--wildfire-seed",
            type=int,
            default=42,
            help="Random seed used to generate the landscape and initial parameters.",
        )
        parser.add_argument(
            "--layer-reps",
            type=int,
            default=2,
            help="Number of layer-optimized circuit repetitions.",
        )

    @classmethod
    def from_namespace(cls, args) -> Self:
        return cls(
            grid_rows=args.grid_rows,
            grid_cols=args.grid_cols,
            shrub_budget=args.shrub_budget,
            brush_probability=args.brush_probability,
            seed=args.wildfire_seed,
            reps=max(1, args.layer_reps),
        )

    def build_problem_data(self, *, logger: logging.Logger) -> WildfireProblemData:
        return WildfireModel.build_problem_data(
            grid_size=(self.grid_rows, self.grid_cols),
            shrub_budget=self.shrub_budget,
            brush_probability=self.brush_probability,
            seed=self.seed,
            logger=logger,
        )

    def build_ansatz(self, *, logger: logging.Logger) -> QuantumCircuit:
        logger.info("Building wildfire circuit via GridQuantumCircuit")
        gamma = ParameterVector("gamma", self.reps)
        beta = ParameterVector("beta", self.reps)
        num_qubits = self.grid_rows * self.grid_cols
        max_active = max(0, min(self.shrub_budget, num_qubits))
        qc = _build_grid_quantum_circuit(
            gamma=list(gamma),
            beta=list(beta),
            grid_size=(self.grid_rows, self.grid_cols),
            max_active=max_active,
        )
        logger.info(
            "Circuit qubits=%s params=%s depth=%s",
            qc.num_qubits,
            qc.num_parameters,
            qc.depth(),
        )
        return qc

    def build_observables(self, layout: Any, problem_data: WildfireProblemData) -> list[list[Any]]:
        if layout is None:
            return [
                list(problem_data.observable_groups[0]),
                list(problem_data.observable_groups[1]),
                list(problem_data.observable_groups[2]),
            ]

        return [
            [op.apply_layout(layout) for op in problem_data.observable_groups[0]],
            [op.apply_layout(layout) for op in problem_data.observable_groups[1]],
            [op.apply_layout(layout) for op in problem_data.observable_groups[2]],
        ]

    def metric_candidates(self) -> tuple[str, ...]:
        return ("fire_break_score", "cut_size")

    def make_loss(
        self,
        *,
        problem_data: WildfireProblemData,
        evaluator: ParameterEvaluator,
        experiment_results: list[dict[str, Any]],
        iteration_times: list[float],
        logger: logging.Logger,
    ) -> Callable[[np.ndarray], float]:
        num_qubits = self.grid_rows * self.grid_cols
        edge_weights = problem_data.edge_weights
        risk_map = problem_data.risk_map.ravel()
        shrub_budget = self.shrub_budget

        def loss_func_estimator(x: np.ndarray) -> float:
            iter_start = time()
            params = np.asarray(x, dtype=float)
            node_exp_map = evaluator(params)
            shrub_scores = WildfireModel.exp_map_to_shrub_scores(node_exp_map, num_qubits)

            unbroken_path_penalty = 0.0
            for edge0, edge1 in problem_data.graph.edge_list():
                edge_weight = float(edge_weights.get((edge0, edge1), 1.0))
                unbroken_path_penalty += edge_weight * (1.0 - shrub_scores[edge0]) * (
                    1.0 - shrub_scores[edge1]
                )

            budget_penalty = float((np.sum(shrub_scores) - shrub_budget) ** 2)
            hotspot_reward = float(np.dot(risk_map, shrub_scores))
            loss = unbroken_path_penalty + 0.5 * budget_penalty - 0.25 * hotspot_reward

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
        self, *, problem_data: WildfireProblemData, experiment_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not experiment_results:
            raise RuntimeError("Optimization completed without producing any iterations.")

        final_exp_map = experiment_results[-1]["exp_map"]
        num_qubits = self.grid_rows * self.grid_cols
        selected_sites = WildfireModel.choose_shrub_sites(
            final_exp_map, self.shrub_budget, num_qubits
        )
        fire_break_score = WildfireModel.calc_fire_break_score(
            problem_data.graph, selected_sites, problem_data.edge_weights
        )
        selected_cells = [
            (idx // self.grid_cols, idx % self.grid_cols) for idx in sorted(selected_sites)
        ]
        cut_size = int(round(fire_break_score))

        return {
            "cut_size": cut_size,
            "fire_break_score": fire_break_score,
            "selected_sites": sorted(selected_sites),
            "selected_cells": selected_cells,
            "exp_map": final_exp_map,
        }

