from dataclasses import dataclass
from itertools import combinations
from time import time
from typing import Any

import rustworkx as rx
from qiskit.quantum_info import SparsePauliOp


@dataclass(frozen=True)
class MaxCutProblemData:
    graph: Any
    pce_x: list[SparsePauliOp]
    pce_y: list[SparsePauliOp]
    pce_z: list[SparsePauliOp]
    setup_time: float
    seed: int


class MaxCutModel:
    """Domain model for generating and scoring MaxCut artifacts."""

    @staticmethod
    def calc_cut_size(graph: Any, partition0: set[int], partition1: set[int]) -> int:
        cut_size = 0
        for edge0, edge1 in graph.edge_list():
            if edge0 in partition0 and edge1 in partition1:
                cut_size += 1
            elif edge0 in partition1 and edge1 in partition0:
                cut_size += 1
        return cut_size

    @staticmethod
    def build_pauli_correlation_encoding(
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

    @classmethod
    def build_problem_data(
        cls,
        *,
        num_nodes: int,
        num_qubits: int,
        graph_probability: float,
        seed: int,
    ) -> MaxCutProblemData:
        print("Creating MaxCut problem with Pauli Correlation Encoding...")
        start_problem = time()

        graph = rx.undirected_gnp_random_graph(num_nodes, graph_probability, seed=seed)
        print(f"Graph: {num_nodes} nodes, {len(graph.edges())} edges")

        list_size = num_nodes // 3
        node_x = [i for i in range(list_size)]
        node_y = [i for i in range(list_size, 2 * list_size)]
        node_z = [i for i in range(2 * list_size, num_nodes)]

        pce_x = cls.build_pauli_correlation_encoding("X", node_x, num_qubits)
        pce_y = cls.build_pauli_correlation_encoding("Y", node_y, num_qubits)
        pce_z = cls.build_pauli_correlation_encoding("Z", node_z, num_qubits)

        setup_time = time() - start_problem
        print(f"✓ Problem setup completed in {setup_time:.4f}s\n")

        return MaxCutProblemData(
            graph=graph,
            pce_x=pce_x,
            pce_y=pce_y,
            pce_z=pce_z,
            setup_time=setup_time,
            seed=seed,
        )

    @staticmethod
    def build_partitions(exp_map: dict[int, float]) -> tuple[set[int], set[int]]:
        partition0, partition1 = set(), set()
        for node_id, value in exp_map.items():
            if value >= 0:
                partition0.add(node_id)
            else:
                partition1.add(node_id)
        return partition0, partition1


