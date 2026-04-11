import argparse
from typing import TypeAlias

from executors import Executor, QBraidExecutor, QiskitExecutor
from problems import MaxCutProblem, Problem

ProblemType: TypeAlias = type[Problem]
ExecutorType: TypeAlias = type[Executor]

PROBLEMS: dict[str, ProblemType] = {
    "maxcut": MaxCutProblem,
}

EXECUTORS: dict[str, ExecutorType] = {
    "qiskit": QiskitExecutor,
    "qbraid": QBraidExecutor,
}


def _parse_selection(argv: list[str] | None = None) -> argparse.Namespace:
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--problem", choices=tuple(PROBLEMS), default="maxcut")
    selector.add_argument("--executor", choices=tuple(EXECUTORS), default="qiskit")
    return selector.parse_known_args(argv)[0]


def build_parser(
    problem_cls: ProblemType = MaxCutProblem,
    executor_cls: ExecutorType = QiskitExecutor,
    *,
    problem_name: str = "maxcut",
    executor_name: str = "qiskit",
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the MaxCut benchmark on IBM hardware, an Aer simulator seeded "
            "from hardware, or a Clifford stabilizer simulator."
        )
    )
    parser.add_argument(
        "--problem",
        choices=tuple(PROBLEMS),
        default=problem_name,
        help="Problem implementation to run.",
    )
    parser.add_argument(
        "--executor",
        choices=tuple(EXECUTORS),
        default=executor_name,
        help="Executor backend to run.",
    )
    problem_cls.add_cli_arguments(parser)
    executor_cls.add_cli_arguments(parser)
    return parser


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    selected = _parse_selection(argv)
    problem_cls = PROBLEMS[selected.problem]
    executor_cls = EXECUTORS[selected.executor]
    return build_parser(
        problem_cls,
        executor_cls,
        problem_name=selected.problem,
        executor_name=selected.executor,
    ).parse_args(argv)


def run_pipeline(
    args: argparse.Namespace,
) -> dict[str, object]:
    problem_cls = PROBLEMS[args.problem]
    executor_cls = EXECUTORS[args.executor]
    problem = problem_cls.from_namespace(args)
    executor = executor_cls.from_namespace(args)
    return executor.execute(problem)


def main(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    return run_pipeline(args)


if __name__ == "__main__":
    main()

