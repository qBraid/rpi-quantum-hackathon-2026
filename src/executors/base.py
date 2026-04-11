from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Any, Self

from problems.base import CliArgumentProvider, Problem


class Executor(CliArgumentProvider, ABC):
    @classmethod
    @abstractmethod
    def add_cli_arguments(cls, parser: ArgumentParser) -> None:
        """Register executor-specific CLI arguments."""
    @classmethod
    @abstractmethod
    def from_namespace(cls, args: Namespace) -> Self:
        """Build an executor from parsed CLI arguments."""

    @property
    @abstractmethod
    def run_label(self) -> str:
        """Human-readable label for this configured executor run."""

    @property
    @abstractmethod
    def benchmark_topics(self) -> set[str]:
        """Benchmark topics this executor can produce for comparisons."""

    @abstractmethod
    def execute(self, problem: Problem) -> dict[str, Any]:
        """Run the problem and return a result summary."""
