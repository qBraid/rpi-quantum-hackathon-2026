from __future__ import annotations
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Any
from problems.base import Problem
class Executor(ABC):
    @classmethod
    @abstractmethod
    def add_cli_arguments(cls, parser: ArgumentParser) -> None:
        """Register executor-specific CLI arguments."""
    @classmethod
    @abstractmethod
    def from_namespace(cls, args: Namespace) -> Executor:
        """Build an executor from parsed CLI arguments."""
    @abstractmethod
    def execute(self, problem: Problem) -> dict[str, Any]:
        """Run the problem and return a result summary."""
