import argparse
import time
import sys
from dataclasses import dataclass
from typing import Any, TypeAlias

import matplotlib.pyplot as plt

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
        "--headless",
        action="store_true",
        help="Disable all wildfire visualization windows (2D and 3D).",
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


def _show_best_wildfire_views(
    *,
    result: dict[str, Any],
    show_wildfire_result,
    show_wildfire_result_3d,
    open_figures: list[plt.Figure],
    open_plotters: list[Any],
    current_figure: plt.Figure | None,
    current_plotter: Any | None,
) -> tuple[plt.Figure | None, Any | None]:
    postprocess = result.get("postprocess")
    if not isinstance(postprocess, dict):
        return current_figure, current_plotter

    if current_figure is not None and plt.fignum_exists(current_figure.number):
        plt.close(current_figure)
    if current_plotter is not None and not getattr(current_plotter, "_closed", True):
        try:
            current_plotter.close()
        except Exception:
            pass

    figure = show_wildfire_result(
        postprocess,
        title=f"Wildfire Mitigation - BEST ({result.get('combination')})",
        block=False,
    )
    plotter = None
    if show_wildfire_result_3d is not None:
        plotter = show_wildfire_result_3d(
            postprocess,
            title=f"Wildfire Mitigation (3D) - BEST ({result.get('combination')})",
            block=False,
        )

    if figure is not None:
        open_figures.append(figure)
    if plotter is not None:
        open_plotters.append(plotter)
    return figure, plotter


def run_pipeline(args: argparse.Namespace) -> dict[str, object]:
    problem_cls = PROBLEMS[args.problem]
    problem = problem_cls.from_namespace(args)
    optimizer = _build_optimizer(args)
    runs = _build_executor_runs(args, optimizer=optimizer)

    should_use_dashboard = (
        args.problem == "wildfire"
        and args.run_matrix
        and any(isinstance(run.executor, QBraidExecutor) for run in runs)
    )

    immediate_runs = list(runs)
    deferred_qbraid_hardware_runs: list[ExecutorRun] = []
    if should_use_dashboard:
        immediate_runs = []
        for run in runs:
            if isinstance(run.executor, QBraidExecutor) and run.executor.environment == "hardware":
                deferred_qbraid_hardware_runs.append(run)
            else:
                immediate_runs.append(run)

    show_hardware_button = bool(deferred_qbraid_hardware_runs)

    dashboard = None
    live_problem_cls = None
    current_best_result: dict[str, Any] | None = None
    open_figures: list[plt.Figure] = []
    open_plotters: list[Any] = []
    best_figure: plt.Figure | None = None
    best_plotter: Any | None = None
    all_results: list[dict[str, Any]] = []

    show_wildfire_result = None
    show_wildfire_result_3d = None
    should_plot_wildfire = args.problem == "wildfire" and not args.headless
    if should_plot_wildfire:
        from utils.wildfire_3d_visualization import show_wildfire_result_3d
        from utils.wildfire_visualization import show_wildfire_result

    def on_dashboard_hardware_result(result: dict[str, Any]) -> None:
        nonlocal current_best_result, best_figure, best_plotter
        all_results.append(result)
        new_best = _select_best_result(all_results)
        if new_best is current_best_result or not should_plot_wildfire or show_wildfire_result is None:
            current_best_result = new_best
            return

        current_best_result = new_best
        if new_best is result:
            best_figure, best_plotter = _show_best_wildfire_views(
                result=new_best,
                show_wildfire_result=show_wildfire_result,
                show_wildfire_result_3d=show_wildfire_result_3d,
                open_figures=open_figures,
                open_plotters=open_plotters,
                current_figure=best_figure,
                current_plotter=best_plotter,
            )

    if should_use_dashboard:
        from dashboard import BenchmarkDashboard, LiveProblem as DashboardLiveProblem

        dashboard = BenchmarkDashboard()
        live_problem_cls = DashboardLiveProblem
        dashboard_qbraid_strategies = [
            run.executor.strategy
            for run in deferred_qbraid_hardware_runs
            if isinstance(run.executor, QBraidExecutor)
        ]
        dashboard.setup_qpu(
            problem=problem,
            optimizer=optimizer,
            backend=args.backend,
            shots=args.qbraid_shots,
            strategies=dashboard_qbraid_strategies,
            on_result=on_dashboard_hardware_result,
        )

    benchmark_topics: set[str] = set()
    benchmark_enabled = False

    for run in immediate_runs:
        print(f"\n--- Running {run.executor.run_label} ---")
        if dashboard is not None and isinstance(run.executor, QBraidExecutor):
            assert live_problem_cls is not None
            dashboard.set_current_run(f"{run.executor.strategy}/{run.executor.environment}")
            live_problem = live_problem_cls(problem, on_iteration=dashboard.record_iteration)
            result = run.executor.execute(live_problem, optimizer=optimizer)
        else:
            result = run.executor.execute(problem, optimizer=optimizer)
        result["combination"] = run.name
        all_results.append(result)

        if dashboard is not None and isinstance(run.executor, QBraidExecutor):
            dashboard.add_result(result)

    if all_results:
        current_best_result = _select_best_result(all_results)
        if should_plot_wildfire and show_wildfire_result is not None:
            best_figure, best_plotter = _show_best_wildfire_views(
                result=current_best_result,
                show_wildfire_result=show_wildfire_result,
                show_wildfire_result_3d=show_wildfire_result_3d,
                open_figures=open_figures,
                open_plotters=open_plotters,
                current_figure=best_figure,
                current_plotter=best_plotter,
            )

    if dashboard is not None:
        dashboard_fig = dashboard.finalize(block=False, show_hardware_button=show_hardware_button)
        open_figures.append(dashboard_fig)

    if open_figures or open_plotters:
        while True:
            active_figures = [fig for fig in open_figures if plt.fignum_exists(fig.number)]
            active_plotters = [plotter for plotter in open_plotters if not getattr(plotter, "_closed", True)]
            if not active_figures and not active_plotters:
                break
            for fig in active_figures:
                try:
                    fig.canvas.flush_events()
                except Exception:
                    continue
            for plotter in active_plotters:
                try:
                    plotter.update()
                    plotter.iren.process_events()
                except Exception:
                    continue
            time.sleep(0.05)

    if not all_results:
        print("No benchmark results were produced.")
        return {
            "problem": args.problem,
            "optimizer": optimizer.label,
            "benchmark_enabled": False,
            "benchmark_summary": None,
            "results": [],
            "best_result": None,
        }

    best_result = _select_best_result(all_results)

    result_topic_sets = {
        frozenset(topic for topic in item.get("benchmark_topics", []) if isinstance(topic, str))
        for item in all_results
    }
    if len(result_topic_sets) == 1:
        benchmark_topics = set(next(iter(result_topic_sets)))
        benchmark_enabled = bool(benchmark_topics)

    benchmark_summary: dict[str, Any] | None = None
    if benchmark_enabled:
        best_benchmark = _select_best_benchmark_result(all_results, benchmark_topics)
        benchmark_summary = {
            "topics": sorted(benchmark_topics),
            "best_combination": best_benchmark.get("combination"),
            "best_run_label": best_benchmark.get("run_label"),
        }
    elif len(all_results) > 1:
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

    if open_figures or open_plotters:

        plt.close("all")
        for plotter in open_plotters:
            try:
                plotter.close()
            except Exception:
                continue
        try:
            from matplotlib.backends import _macosx

            stop = getattr(_macosx, "stop", None)
            if callable(stop):
                stop()
        except Exception:
            pass


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

