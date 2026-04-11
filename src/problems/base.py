from __future__ import annotations

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Any, Callable, Protocol

import numpy as np
from qiskit.circuit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp


class ParameterEvaluator(Protocol):
    def __call__(self, params: np.ndarray) -> dict[int, float]:
        """Return an expectation-value map for the supplied parameters."""


class Problem(ABC):
    @classmethod
    @abstractmethod
    def add_cli_arguments(cls, parser: ArgumentParser) -> None:
        """Register problem-specific CLI arguments."""

    @classmethod
    @abstractmethod
    def from_namespace(cls, args: Namespace) -> Problem:
        """Build a problem instance from parsed CLI arguments."""

    @abstractmethod
    def build_problem_data(self) -> Any:
        """Prepare runtime-independent problem data."""

    @abstractmethod
    def build_ansatz(self) -> QuantumCircuit:
        """Construct the problem ansatz circuit."""

    @abstractmethod
    def build_observables(
        self, layout: Any, problem_data: Any
    ) -> list[list[SparsePauliOp]]:
        """Apply a transpiled layout to the problem observables."""

    @abstractmethod
    def make_loss(
        self,
        *,
        problem_data: Any,
        evaluator: ParameterEvaluator,
        experiment_results: list[dict[str, Any]],
        iteration_times: list[float],
    ) -> Callable[[np.ndarray], float]:
        """Create the optimization objective using an injected evaluator."""

    @abstractmethod
    def postprocess(
        self, *, problem_data: Any, experiment_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Convert the final experiment output into domain-specific results."""

