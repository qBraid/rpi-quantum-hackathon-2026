import argparse
from dataclasses import dataclass
from typing import Any, TypeAlias

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


@dataclass(frozen=True)
class ExecutorRun:
    name: str
    executor: Executor


def build_parser(problem_cls: ProblemType = MaxCutProblem) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run benchmark workloads and compare executor combinations when "
            "their benchmark topics are compatible."
        )
    )
    parser.add_argument(
        "--problem",
        choices=tuple(PROBLEMS),
        default="maxcut",
        help="Problem implementation to run.",
    )
    parser.add_argument(
        "--executor",
        choices=tuple(EXECUTORS),
        default="qiskit",
        help="Executor backend for single-run mode.",
    )
    parser.add_argument(
        "--run-matrix",
        action="store_true",
        help="Run all requested executor/option combinations.",
    )
    parser.add_argument(
        "--benchmark-executors",
        nargs="+",
        choices=tuple(EXECUTORS),
        default=None,
        help="Executors to include in matrix mode.",
    )
    parser.add_argument(
        "--benchmark-qiskit-modes",
        nargs="+",
        choices=("hardware", "aer", "clifford"),
        default=["clifford"],
        help="Qiskit modes to include in matrix mode.",
    )
    parser.add_argument(
        "--benchmark-qbraid-strategies",
        nargs="+",
        choices=("balanced", "aggressive"),
        default=["balanced", "aggressive"],
        help="qBraid strategies to include in matrix mode.",
    )
    parser.add_argument(
        "--benchmark-qbraid-environments",
        nargs="+",
        choices=("hardware", "aer", "clifford"),
        default=["aer", "clifford"],
        help="qBraid environments to include in matrix mode.",
    )

    problem_cls.add_cli_arguments(parser)
    QiskitExecutor.add_cli_arguments(parser)
    QBraidExecutor.add_cli_arguments(parser)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def _build_executor_runs(args: argparse.Namespace) -> list[ExecutorRun]:
    if not args.run_matrix:
        executor_cls = EXECUTORS[args.executor]
        return [ExecutorRun(name=args.executor, executor=executor_cls.from_namespace(args))]

    selected = args.benchmark_executors if args.benchmark_executors else [args.executor]
    runs: list[ExecutorRun] = []

    for executor_name in selected:
        if executor_name == "qiskit":
            for mode in args.benchmark_qiskit_modes:
                runs.append(
                    ExecutorRun(
                        name=f"qiskit(mode={mode})",
                        executor=QiskitExecutor(
                            mode=mode,
                            backend_name=args.backend,
                            maxiter=args.maxiter,
                        ),
                    )
                )
            continue

        for strategy in args.benchmark_qbraid_strategies:
            for environment in args.benchmark_qbraid_environments:
                runs.append(
                    ExecutorRun(
                        name=(
                            "qbraid("
                            f"strategy={strategy},"
                            f"environment={environment}"
                            ")"
                        ),
                        executor=QBraidExecutor(
                            backend_name=args.backend,
                            maxiter=args.maxiter,
                            strategy=strategy,
                            environment=environment,
                        ),
                    )
                )

    return runs


def _select_best_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    def key(item: dict[str, Any]) -> tuple[float, float]:
        cut_size = item.get("cut_size")
        cut_score = float(cut_size) if isinstance(cut_size, int) else float("-inf")
        final_loss = item.get("final_loss")
        loss_score = -float(final_loss) if isinstance(final_loss, (int, float)) else float("-inf")
        return (cut_score, loss_score)

    return max(results, key=key)


def _select_best_benchmark_result(
    results: list[dict[str, Any]], benchmark_topics: set[str]
) -> dict[str, Any]:
    if "tradeoff_score" in benchmark_topics:
        return max(results, key=lambda item: float(item.get("tradeoff_score", float("-inf"))))
    if "quality_score" in benchmark_topics:
        return max(results, key=lambda item: float(item.get("quality_score", float("-inf"))))
    if "compiled_resource_cost" in benchmark_topics:
        return min(results, key=lambda item: float(item.get("compiled_resource_cost", float("inf"))))
    return _select_best_result(results)


def run_pipeline(args: argparse.Namespace) -> dict[str, object]:
    problem_cls = PROBLEMS[args.problem]
    problem = problem_cls.from_namespace(args)
    runs = _build_executor_runs(args)

    topic_sets = [frozenset(run.executor.benchmark_topics) for run in runs]
    unique_topic_sets = set(topic_sets)
    benchmark_topics = set(topic_sets[0]) if topic_sets else set()
    benchmark_enabled = len(unique_topic_sets) == 1 and bool(benchmark_topics)

    all_results: list[dict[str, Any]] = []
    for run in runs:
        print(f"\n--- Running {run.executor.run_label} ---")
        result = run.executor.execute(problem)
        result["combination"] = run.name
        all_results.append(result)

    best_result = _select_best_result(all_results)

    benchmark_summary: dict[str, Any] | None = None
    if benchmark_enabled:
        best_benchmark = _select_best_benchmark_result(all_results, benchmark_topics)
        benchmark_summary = {
            "topics": sorted(benchmark_topics),
            "best_combination": best_benchmark.get("combination"),
            "best_run_label": best_benchmark.get("run_label"),
        }
    elif len(runs) > 1:
        print(
            "Skipping benchmark comparison: combinations expose different benchmark topics."
        )

    print("=" * 70)
    print("COMBINATION SUMMARY")
    print("=" * 70)
    for item in all_results:
        print(
            f"{item.get('combination')}: cut={item.get('cut_size')} "
            f"loss={item.get('final_loss')} topics={item.get('benchmark_topics')}"
        )
    print(
        "Best result: "
        f"{best_result.get('combination')} "
        f"(run={best_result.get('run_label')})"
    )
    print("=" * 70)

    return {
        "problem": args.problem,
        "benchmark_enabled": benchmark_enabled,
        "benchmark_summary": benchmark_summary,
        "results": all_results,
        "best_result": best_result,
    }


def main(argv: list[str] | None = None) -> dict[str, object]:
    args = parse_args(argv)
    return run_pipeline(args)


if __name__ == "__main__":
    main()

