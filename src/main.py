import argparse
from typing import TypeAlias

from executors import Executor, QiskitExecutor
from problems import MaxCutProblem, Problem

ProblemType: TypeAlias = type[Problem]
ExecutorType: TypeAlias = type[Executor]


def build_parser(
    problem_cls: ProblemType = MaxCutProblem,
    executor_cls: ExecutorType = QiskitExecutor,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the MaxCut benchmark on IBM hardware, an Aer simulator seeded "
            "from hardware, or a Clifford stabilizer simulator."
        )
    )
    problem_cls.add_cli_arguments(parser)
    executor_cls.add_cli_arguments(parser)
    return parser


def parse_args(
    argv: list[str] | None = None,
    problem_cls: ProblemType = MaxCutProblem,
    executor_cls: ExecutorType = QiskitExecutor,
) -> argparse.Namespace:
    return build_parser(problem_cls, executor_cls).parse_args(argv)


def run_pipeline(
    args: argparse.Namespace,
    problem_cls: ProblemType = MaxCutProblem,
    executor_cls: ExecutorType = QiskitExecutor,
) -> dict[str, object]:
    problem = problem_cls.from_namespace(args)
    executor = executor_cls.from_namespace(args)
    return executor.execute(problem)


def main(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv, MaxCutProblem, QiskitExecutor)
    return run_pipeline(args, MaxCutProblem, QiskitExecutor)


if __name__ == "__main__":
    main()

