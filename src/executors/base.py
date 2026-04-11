from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
import logging
import sys
from typing import Any, Self

from optimizers import Optimizer
from problems.base import CliArgumentProvider, Problem


class Executor(CliArgumentProvider, ABC):
    @classmethod
    @abstractmethod
    def add_cli_arguments(cls, parser: ArgumentParser) -> None:
        """Register executor-specific CLI arguments."""
    @classmethod
    @abstractmethod
    def from_namespace(cls, args: Namespace, *, optimizer: Optimizer) -> Self:
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
    def execute(self, problem: Problem, *, optimizer: Optimizer) -> dict[str, Any]:
        """Run the problem and return a result summary."""


class _ExecutorColorFormatter(logging.Formatter):
    _RESET = "\033[0m"
    _NAME = "\033[36m"
    _LEVEL_COLORS = {
        logging.DEBUG: "\033[90m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }

    def __init__(self, *, use_color: bool) -> None:
        super().__init__("[%(name)s] %(message)s")
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if not self._use_color:
            return super().format(record)

        message = record.getMessage()
        level_color = self._LEVEL_COLORS.get(record.levelno, "")
        name = f"{self._NAME}{record.name}{self._RESET}"
        body = f"{level_color}{message}{self._RESET}" if level_color else message
        return f"[{name}] {body}"


def get_executor_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        use_color = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
        handler.setFormatter(_ExecutorColorFormatter(use_color=use_color))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


