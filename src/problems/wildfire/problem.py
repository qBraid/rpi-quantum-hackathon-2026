from dataclasses import dataclass
import logging
from time import time
from typing import Any, Callable, Self

import numpy as np
from qiskit.circuit import ParameterVector, QuantumCircuit
from GPTCircuitImproved import GridQuantumCircuit

from problems.base import ParameterEvaluator, Problem, format_float, format_float_list

from .model import WildfireModel, WildfireProblemData


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
        logger.info("Building wildfire circuit via GPTCircuitImproved.GridQuantumCircuit")
        gamma = ParameterVector("gamma", self.reps)
        beta = ParameterVector("beta", self.reps)
        num_qubits = self.grid_rows * self.grid_cols
        max_active = max(0, min(self.shrub_budget, num_qubits))
        qc = GridQuantumCircuit(
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

    @staticmethod
    def _format_parameter_list(values: list[float], precision: int = 6) -> str:
        return format_float_list(values, precision=precision)

    def describe_parameters(self, params: np.ndarray) -> dict[str, Any]:
        values = np.asarray(params, dtype=float)
        reps = max(self.reps, 1)
        gamma = [float(v) for v in values[:reps]]
        beta = [float(v) for v in values[reps : 2 * reps]]
        return {
            "gamma": gamma,
            "beta": beta,
            "gamma_fmt": self._format_parameter_list(gamma),
            "beta_fmt": self._format_parameter_list(beta),
            "params": [float(v) for v in values],
        }


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
        shrub_budget = self.shrub_budget

        def loss_func_estimator(x: np.ndarray) -> float:
            iter_start = time()
            params = np.asarray(x, dtype=float)
            node_exp_map = evaluator(params)
            shrub_scores = WildfireModel.exp_map_to_shrub_scores(node_exp_map, num_qubits)
            param_view = self.describe_parameters(params)

            edge_penalty = 0.0
            for edge0, edge1 in problem_data.graph.edge_list():
                edge_penalty += (1.0 - shrub_scores[edge0]) * (1.0 - shrub_scores[edge1])

            budget_penalty = float((np.sum(shrub_scores) - shrub_budget) ** 2)
            loss = edge_penalty + budget_penalty

            iter_time = time() - iter_start
            iteration_times.append(iter_time)
            logger.info(
                "Iteration %3d loss=%s gamma=%s beta=%s time=%s",
                len(experiment_results),
                format_float(loss),
                param_view["gamma_fmt"],
                param_view["beta_fmt"],
                format_float(iter_time),
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
            "grid_size": [self.grid_rows, self.grid_cols],
            "shrub_budget": self.shrub_budget,
            "fuel_map": problem_data.fuel_map.tolist(),
            "risk_map": problem_data.risk_map.tolist(),
            "exp_map": final_exp_map,
        }

