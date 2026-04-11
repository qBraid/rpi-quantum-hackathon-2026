import argparse
import sys
from dataclasses import dataclass
from typing import Any, TypeAlias

from executors import Executor, QBraidExecutor, QiskitExecutor
from optimizers import Optimizer, ScipyOptimizer, SpsaOptimizer
from problems import MaxCutProblem, Problem, WildfireMitigationProblem
from problems.base import format_float

ProblemType: TypeAlias = type[Problem]
ExecutorType: TypeAlias = type[Executor]
OptimizerType: TypeAlias = type[Optimizer]

PROBLEMS: dict[str, ProblemType] = {
    "maxcut": MaxCutProblem,
    "wildfire": WildfireMitigationProblem,
}

EXECUTORS: dict[str, ExecutorType] = {
    "qiskit": QiskitExecutor,
    "qbraid": QBraidExecutor,
}

OPTIMIZERS: dict[str, OptimizerType] = {
    "scipy": ScipyOptimizer,
    "spsa": SpsaOptimizer,
}


@dataclass(frozen=True)
class ExecutorRun:
    name: str
    executor: Executor


def build_parser() -> argparse.ArgumentParser:
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
        choices=("hardware", "aer", "clifford", "cloud"),
        default=["aer", "clifford"],
        help="qBraid environments to include in matrix mode.",
    )
    parser.add_argument(
        "--no-wildfire-plot",
        action="store_true",
        help="Disable matplotlib visualization for wildfire runs (all combinations/invocations).",
    )
    parser.add_argument(
        "--optimizer-backend",
        choices=tuple(OPTIMIZERS) + ("auto",),
        default="auto",
        help="Optimizer backend implementation.",
    )
    parser.add_argument(
        "--maxiter",
        type=int,
        default=None,
        help="Backward-compatible alias for optimizer iteration/evaluation budget.",
    )

    for problem_cls in PROBLEMS.values():
        problem_cls.add_cli_arguments(parser)
    for optimizer_cls in OPTIMIZERS.values():
        optimizer_cls.add_cli_arguments(parser)
    QiskitExecutor.add_cli_arguments(parser)
    QBraidExecutor.add_cli_arguments(parser)
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    normalized_argv = list(sys.argv[1:] if argv is None else argv)
    has_problem_flag = any(
        token == "--problem" or token.startswith("--problem=") for token in normalized_argv
    )
    has_wildfire_hint = any(
        token in {
            "--grid-rows",
            "--grid-cols",
            "--shrub-budget",
            "--brush-probability",
            "--wildfire-seed",
            "--layer-reps",
        }
        for token in normalized_argv
    )

    if not has_problem_flag and has_wildfire_hint:
        normalized_argv = ["--problem", "wildfire", *normalized_argv]

    return build_parser().parse_args(normalized_argv)


def _build_optimizer(args: argparse.Namespace) -> Optimizer:
    if args.maxiter is not None:
        args.optimizer_maxiter = int(args.maxiter)
        args.spsa_maxiter = int(args.maxiter)

    if args.optimizer_backend == "auto":
        if args.problem == "wildfire":
            return SpsaOptimizer.from_namespace(args)
        return ScipyOptimizer.from_namespace(args)

    optimizer_cls = OPTIMIZERS[args.optimizer_backend]
    return optimizer_cls.from_namespace(args)


def _build_executor_runs(args: argparse.Namespace, *, optimizer: Optimizer) -> list[ExecutorRun]:
    if not args.run_matrix:
        executor_cls = EXECUTORS[args.executor]
        return [
            ExecutorRun(
                name=args.executor,
                executor=executor_cls.from_namespace(args, optimizer=optimizer),
            )
        ]

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
                            strategy=strategy,
                            environment=environment,
                            qbraid_shots=args.qbraid_shots,
                        ),
                    )
                )

    return runs


def _select_best_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    def key(item: dict[str, Any]) -> tuple[float, float]:
        primary_metric_value = item.get("primary_metric_value")
        primary_score = (
            float(primary_metric_value)
            if isinstance(primary_metric_value, (int, float))
            else float("-inf")
        )
        cut_size = item.get("cut_size")
        cut_score = float(cut_size) if isinstance(cut_size, (int, float)) else float("-inf")
        final_loss = item.get("final_loss")
        loss_score = -float(final_loss) if isinstance(final_loss, (int, float)) else float("-inf")
        return (primary_score if primary_score != float("-inf") else cut_score, loss_score)

    return max(results, key=key)


def _format_primary_metric(item: dict[str, Any]) -> tuple[str, Any]:
    metric_name = item.get("primary_metric_name")
    metric_value = item.get("primary_metric_value")
    if metric_name is not None and metric_value is not None:
        return str(metric_name), metric_value

    if "cut_size" in item:
        return "cut_size", item.get("cut_size")
    if "fire_break_score" in item:
        return "fire_break_score", item.get("fire_break_score")
    if "quality_score" in item:
        return "quality_score", item.get("quality_score")

    return "metric", item.get("final_loss")


def _format_metric_value(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return format_float(value)
    return value


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
    optimizer = _build_optimizer(args)
    runs = _build_executor_runs(args, optimizer=optimizer)

    topic_sets = [frozenset(run.executor.benchmark_topics) for run in runs]
    unique_topic_sets = set(topic_sets)
    benchmark_topics = set(topic_sets[0]) if topic_sets else set()
    benchmark_enabled = len(unique_topic_sets) == 1 and bool(benchmark_topics)

    show_wildfire_result = None
    should_plot_wildfire = args.problem == "wildfire" and not args.no_wildfire_plot
    if should_plot_wildfire:
        from utils.wildfire_visualization import show_wildfire_result

    all_results: list[dict[str, Any]] = []
    for idx, run in enumerate(runs):
        print(f"\n--- Running {run.executor.run_label} ---")
        result = run.executor.execute(problem, optimizer=optimizer)
        result["combination"] = run.name
        all_results.append(result)

        if should_plot_wildfire and show_wildfire_result is not None:
            postprocess = result.get("postprocess")
            if isinstance(postprocess, dict):
                show_wildfire_result(
                    postprocess,
                    title=f"Wildfire Mitigation - {run.name}",
                    block=(idx == len(runs) - 1),
                )

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
        metric_name, metric_value = _format_primary_metric(item)
        print(
            f"{item.get('combination')}: {metric_name}={_format_metric_value(metric_value)} "
            f"loss={_format_metric_value(item.get('final_loss'))} topics={item.get('benchmark_topics')}"
        )
    best_metric_name, best_metric_value = _format_primary_metric(best_result)
    print(
        "Best result: "
        f"{best_result.get('combination')} "
        f"(run={best_result.get('run_label')}, {best_metric_name}={_format_metric_value(best_metric_value)})"
    )
    print("=" * 70)


    return {
        "problem": args.problem,
        "optimizer": optimizer.label,
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

