from dataclasses import dataclass
import logging
from time import time
from typing import Any

import numpy as np
import rustworkx as rx
from qiskit.quantum_info import SparsePauliOp


def _cell_index(row: int, col: int, cols: int) -> int:
    return row * cols + col


def _single_qubit_z_observable(qubit_index: int, num_qubits: int) -> SparsePauliOp:
    paulis = ["I"] * num_qubits
    paulis[qubit_index] = "Z"
    return SparsePauliOp.from_list([("".join(paulis)[::-1], 1.0)])


@dataclass(frozen=True)
class WildfireProblemData:
    graph: Any
    fuel_map: np.ndarray
    risk_map: np.ndarray
    edge_weights: dict[tuple[int, int], float]
    observable_groups: tuple[list[SparsePauliOp], list[SparsePauliOp], list[SparsePauliOp]]
    grid_size: tuple[int, int]
    shrub_budget: int
    setup_time: float
    seed: int


class WildfireModel:
    """Domain model for the wildfire mitigation benchmark."""

    @staticmethod
    def build_observable_groups(num_qubits: int) -> tuple[list[SparsePauliOp], list[SparsePauliOp], list[SparsePauliOp]]:
        groups: list[list[SparsePauliOp]] = [[], [], []]
        for qubit_index in range(num_qubits):
            groups[qubit_index % 3].append(_single_qubit_z_observable(qubit_index, num_qubits))
        return groups[0], groups[1], groups[2]

    @classmethod
    def build_problem_data(
        cls,
        *,
        grid_size: tuple[int, int],
        shrub_budget: int,
        brush_probability: float,
        seed: int,
        logger: logging.Logger,
    ) -> WildfireProblemData:
        logger.info("Creating wildfire mitigation problem instance")
        start_problem = time()

        rows, cols = grid_size
        num_qubits = rows * cols
        rng = np.random.default_rng(seed)

        fuel_map = (rng.random((rows, cols)) < brush_probability).astype(float)
        row_gradient = np.linspace(1.35, 0.85, rows, dtype=float)[:, None]
        col_gradient = np.linspace(0.9, 1.1, cols, dtype=float)[None, :]
        risk_map = row_gradient * col_gradient * (0.65 + 0.35 * fuel_map)

        graph = rx.PyGraph()
        graph.add_nodes_from(range(num_qubits))
        edge_weights: dict[tuple[int, int], float] = {}

        for row in range(rows):
            for col in range(cols):
                idx = _cell_index(row, col, cols)
                if col + 1 < cols:
                    right = _cell_index(row, col + 1, cols)
                    weight = 1.0 + 0.5 * float(risk_map[row, col] + risk_map[row, col + 1])
                    graph.add_edge(idx, right, weight)
                    edge_weights[(idx, right)] = weight
                if row + 1 < rows:
                    below = _cell_index(row + 1, col, cols)
                    weight = 1.0 + 0.5 * float(risk_map[row, col] + risk_map[row + 1, col])
                    graph.add_edge(idx, below, weight)
                    edge_weights[(idx, below)] = weight

        observable_groups = cls.build_observable_groups(num_qubits)
        setup_time = time() - start_problem
        logger.info(
            "Wildfire grid=%sx%s shrubs=%s setup=%.4fs",
            rows,
            cols,
            shrub_budget,
            setup_time,
        )

        return WildfireProblemData(
            graph=graph,
            fuel_map=fuel_map,
            risk_map=risk_map,
            edge_weights=edge_weights,
            observable_groups=observable_groups,
            grid_size=grid_size,
            shrub_budget=shrub_budget,
            setup_time=setup_time,
            seed=seed,
        )

    @staticmethod
    def exp_map_to_shrub_scores(exp_map: dict[int, float], num_qubits: int) -> np.ndarray:
        ordered = np.array([float(exp_map.get(idx, 1.0)) for idx in range(num_qubits)], dtype=float)
        return np.clip((1.0 - ordered) / 2.0, 0.0, 1.0)

    @staticmethod
    def choose_shrub_sites(exp_map: dict[int, float], budget: int, num_qubits: int) -> set[int]:
        shrub_scores = WildfireModel.exp_map_to_shrub_scores(exp_map, num_qubits)
        budget = max(0, min(int(budget), num_qubits))
        if budget == 0:
            return set()
        ranked = np.argsort(-shrub_scores, kind="stable")[:budget]
        return {int(idx) for idx in ranked}

    @staticmethod
    def calc_fire_break_score(
        graph: Any,
        selected_sites: set[int],
        edge_weights: dict[tuple[int, int], float],
    ) -> float:
        fire_break_score = 0.0
        for edge0, edge1 in graph.edge_list():
            if edge0 in selected_sites or edge1 in selected_sites:
                fire_break_score += float(edge_weights.get((edge0, edge1), 1.0))
        return fire_break_score


