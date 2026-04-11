from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
import logging
from typing import Any, Callable, Protocol, Self

import numpy as np


class ParameterEvaluator(Protocol):
    def __call__(self, params: np.ndarray) -> dict[int, float]:
        """Return an expectation-value map for the supplied parameters."""


def format_float_list(values: list[float], precision: int = 6) -> str:
    """Format a list of floats with fixed precision while preserving negative signs."""
    formatted: list[str] = []
    for value in values:
        formatted.append(format_float(value, precision=precision))
    return f"[{', '.join(formatted)}]"


def format_float(value: float, precision: int = 6) -> str:
    """Format a scalar float with fixed precision while preserving negative signs."""
    numeric = float(value)
    if numeric == 0.0 and np.signbit(numeric):
        return f"-{abs(numeric):.{precision}f}"
    return f"{numeric:.{precision}f}"


class CliArgumentProvider(ABC):
    @classmethod
    @abstractmethod
    def add_cli_arguments(cls, parser: ArgumentParser) -> None:
        """Register component-specific CLI arguments."""


class Problem(CliArgumentProvider, ABC):

    @classmethod
    @abstractmethod
    def from_namespace(cls, args: Namespace) -> Self:
        """Build a problem instance from parsed CLI arguments."""

    @abstractmethod
    def build_problem_data(self, *, logger: logging.Logger) -> Any:
        """Prepare runtime-independent problem data."""

    @abstractmethod
    def build_ansatz(self, *, logger: logging.Logger) -> Any:
        """Construct the problem ansatz circuit."""

    @abstractmethod
    def build_observables(self, layout: Any, problem_data: Any) -> list[list[Any]]:
        """Apply a transpiled layout to the problem observables."""

    @abstractmethod
    def metric_candidates(self) -> tuple[str, ...]:
        """Return ordered postprocess keys that identify the problem's primary metric."""


    def describe_parameters(self, params: np.ndarray) -> dict[str, Any]:
        """Return a problem-specific view of optimized parameters for logging/reporting."""
        return {"params": [float(value) for value in np.asarray(params, dtype=float)]}

    @abstractmethod
    def make_loss(
        self,
        *,
        problem_data: Any,
        evaluator: ParameterEvaluator,
        experiment_results: list[dict[str, Any]],
        iteration_times: list[float],
        logger: logging.Logger,
    ) -> Callable[[np.ndarray], float]:
        """Create the optimization objective using an injected evaluator."""

    @abstractmethod
    def postprocess(
        self, *, problem_data: Any, experiment_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Convert the final experiment output into domain-specific results."""

