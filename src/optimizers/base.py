from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from typing import Any, Callable, Protocol, Self

import numpy as np


class ObjectiveFn(Protocol):
    def __call__(self, params: np.ndarray) -> float:
        ...


@dataclass(frozen=True)
class OptimizerResult:
    x: np.ndarray
    fun: float
    raw_result: Any


class Optimizer(ABC):
    @classmethod
    @abstractmethod
    def add_cli_arguments(cls, parser: ArgumentParser) -> None:
        """Register optimizer-specific CLI arguments."""

    @classmethod
    @abstractmethod
    def from_namespace(cls, args: Namespace) -> Self:
        """Build an optimizer from parsed CLI arguments."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable optimizer label."""

    @abstractmethod
    def planned_evaluations(self, *, num_parameters: int) -> int | None:
        """Return a best-effort estimate of objective evaluations."""

    @abstractmethod
    def optimize(self, objective: ObjectiveFn, initial_params: np.ndarray) -> OptimizerResult:
        """Optimize the objective and return optimized parameters/results."""

