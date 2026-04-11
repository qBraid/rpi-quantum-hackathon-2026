from __future__ import annotations

import argparse

from executors import QiskitExecutor
from problems import MaxCutProblem


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the MaxCut benchmark on IBM hardware, an Aer simulator seeded "
            "from hardware, or a Clifford stabilizer simulator."
        )
    )
    MaxCutProblem.add_cli_arguments(parser)
    QiskitExecutor.add_cli_arguments(parser)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> dict[str, object]:
    problem = MaxCutProblem.from_namespace(args)
    executor = QiskitExecutor.from_namespace(args)
    return executor.execute(problem)


def main(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    return run_pipeline(args)


if __name__ == "__main__":
    main()

