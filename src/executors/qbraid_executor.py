from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any, Callable, Self

import numpy as np
from dotenv import load_dotenv
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime import QiskitRuntimeService
from scipy.optimize import minimize

from executors.base import Executor
from problems.base import ParameterEvaluator, Problem


@dataclass(frozen=True)
class CompilationStrategy:
    name: str
    optimization_level: int
    routing_method: str | None = None


@dataclass(frozen=True)
class ExecutionEnvironment:
    name: str
    transpile_backend: Any
    estimator_mode: Any
    parameter_transform: Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class RuntimeMetrics:
    depth: int
    size: int
    two_qubit_ops: int
    transpile_time: float


@dataclass(frozen=True)
class BenchmarkRun:
    strategy: str
    environment: str
    qbraid_used: bool
    final_loss: float
    cut_size: int | None
    quality_score: float
    compiled_resource_cost: float
    tradeoff_score: float
    metrics: RuntimeMetrics


@dataclass(frozen=True)
class QBraidExecutor(Executor):
    backend_name: str
    maxiter: int
    strategies: tuple[str, ...]
    environments: tuple[str, ...]

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        parser.add_argument(
            "--backend",
            default="ibm_rensselaer",
            help="IBM backend name used for runtime-backed environments.",
        )
        parser.add_argument(
            "--maxiter",
            type=int,
            default=5,
            help="Maximum number of COBYLA iterations per strategy/environment run.",
        )
        parser.add_argument(
            "--qbraid-strategies",
            nargs="+",
            choices=("balanced", "aggressive"),
            default=["balanced", "aggressive"],
            help="Compilation strategies to compare.",
        )
        parser.add_argument(
            "--qbraid-environments",
            nargs="+",
            choices=("aer", "clifford"),
            default=["aer", "clifford"],
            help="Execution environments to benchmark.",
        )

    @classmethod
    def from_namespace(cls, args) -> Self:
        return cls(
            backend_name=args.backend,
            maxiter=args.maxiter,
            strategies=tuple(args.qbraid_strategies),
            environments=tuple(args.qbraid_environments),
        )

    @staticmethod
    def _snap_to_clifford_angles(params: np.ndarray) -> np.ndarray:
        params = np.asarray(params, dtype=float)
        step = np.pi / 2
        return np.round(params / step) * step

    def _build_environment(self, name: str) -> ExecutionEnvironment:
        if name == "aer":
            load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
            try:
                service = QiskitRuntimeService()
                backend = service.backend(self.backend_name)
                simulator = AerSimulator.from_backend(backend)
            except Exception:
                simulator = AerSimulator()
            return ExecutionEnvironment(
                name="aer",
                transpile_backend=simulator,
                estimator_mode=simulator,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
            )

        simulator = AerSimulator(method="stabilizer")  # type: ignore[arg-type]
        return ExecutionEnvironment(
            name="clifford",
            transpile_backend=simulator,
            estimator_mode=simulator,
            parameter_transform=self._snap_to_clifford_angles,
        )

    @staticmethod
    def _strategy_catalog(selected: list[str]) -> list[CompilationStrategy]:
        mapping = {
            "balanced": CompilationStrategy(
                name="balanced", optimization_level=1, routing_method="sabre"
            ),
            "aggressive": CompilationStrategy(
                name="aggressive", optimization_level=3, routing_method="sabre"
            ),
        }
        return [mapping[name] for name in selected]

    @staticmethod
    def _make_evaluator(
        *,
        estimator: Estimator,
        ansatz,
        observables: list[list[Any]],
        parameter_transform: Callable[[np.ndarray], np.ndarray],
    ) -> ParameterEvaluator:
        def evaluate(params: np.ndarray) -> dict[int, float]:
            transformed = parameter_transform(np.asarray(params, dtype=float))
            pubs = [
                (ansatz, observables[0], transformed),
                (ansatz, observables[1], transformed),
                (ansatz, observables[2], transformed),
            ]
            job = estimator.run(pubs)  # type: ignore[arg-type]
            result = job.result()

            node_exp_map = {}
            idx = 0
            for entry in result:
                for ev in entry.data.evs:
                    node_exp_map[idx] = ev
                    idx += 1
            return node_exp_map

        return evaluate

    @staticmethod
    def _calc_compiled_resource_cost(metrics: RuntimeMetrics) -> float:
        return (
            float(metrics.depth)
            + 0.1 * float(metrics.size)
            + 10.0 * float(metrics.two_qubit_ops)
            + metrics.transpile_time
        )

    @staticmethod
    def _quality_score(cut_size: int | None, final_loss: float) -> float:
        if cut_size is not None:
            return float(cut_size)
        # If a problem doesn't expose a cut size, optimization objective quality is inverse loss.
        return -float(final_loss)

    @staticmethod
    def _compile_with_qbraid_or_qiskit(
        *,
        circuit,
        strategy: CompilationStrategy,
        transpile_backend: Any,
    ) -> tuple[Any, bool, float]:
        start = time()
        qbraid_used = False

        try:
            from qbraid.transpiler import transpile as qbraid_transpile  # type: ignore

            compiled = qbraid_transpile(
                circuit,
                target="qiskit",
                backend=transpile_backend,
                optimization_level=strategy.optimization_level,
            )
            qbraid_used = True
        except Exception:
            pm_options: dict[str, Any] = {
                "backend": transpile_backend,
                "optimization_level": strategy.optimization_level,
            }
            if strategy.routing_method is not None:
                pm_options["routing_method"] = strategy.routing_method
            pm = generate_preset_pass_manager(**pm_options)
            compiled = pm.run(circuit)

        return compiled, qbraid_used, time() - start

    def _run_single(
        self,
        *,
        problem: Problem,
        problem_data: Any,
        strategy: CompilationStrategy,
        environment: ExecutionEnvironment,
    ) -> BenchmarkRun:
        ansatz = problem.build_ansatz()
        compiled, qbraid_used, transpile_time = self._compile_with_qbraid_or_qiskit(
            circuit=ansatz,
            strategy=strategy,
            transpile_backend=environment.transpile_backend,
        )

        metrics = RuntimeMetrics(
            depth=int(compiled.depth() or 0),
            size=int(compiled.size() or 0),
            two_qubit_ops=int(compiled.num_nonlocal_gates()),
            transpile_time=transpile_time,
        )

        observables = problem.build_observables(compiled.layout, problem_data)
        estimator = Estimator(mode=environment.estimator_mode)
        experiment_results: list[dict[str, Any]] = []
        iteration_times: list[float] = []
        loss_func = problem.make_loss(
            problem_data=problem_data,
            evaluator=self._make_evaluator(
                estimator=estimator,
                ansatz=compiled,
                observables=observables,
                parameter_transform=environment.parameter_transform,
            ),
            experiment_results=experiment_results,
            iteration_times=iteration_times,
        )
        objective: Callable[..., Any] = loss_func

        seed = getattr(problem_data, "seed", 42)
        rng = np.random.default_rng(seed)
        num_parameters = int(compiled.num_parameters)
        initial_params = rng.random(num_parameters)
        min_required_iters = num_parameters + 2
        maxiter = max(self.maxiter, min_required_iters)

        minimize_options: dict[str, int] = {"maxiter": maxiter}
        _ = minimize(
            objective,
            initial_params,
            method="COBYLA",
            options=minimize_options,
        )  # type: ignore[arg-type, call-overload]

        postprocess = problem.postprocess(
            problem_data=problem_data, experiment_results=experiment_results
        )
        final_loss = (
            float(experiment_results[-1]["loss"]) if experiment_results else float("inf")
        )
        cut_size = postprocess.get("cut_size")
        if isinstance(cut_size, bool):
            cut_size = None
        if isinstance(cut_size, (int, np.integer)):
            cut_size = int(cut_size)
        else:
            cut_size = None

        quality_score = self._quality_score(cut_size=cut_size, final_loss=final_loss)
        resource_cost = self._calc_compiled_resource_cost(metrics)
        tradeoff_score = quality_score / max(resource_cost, 1e-9)

        return BenchmarkRun(
            strategy=strategy.name,
            environment=environment.name,
            qbraid_used=qbraid_used,
            final_loss=final_loss,
            cut_size=cut_size,
            quality_score=quality_score,
            compiled_resource_cost=resource_cost,
            tradeoff_score=tradeoff_score,
            metrics=metrics,
        )

    def execute(self, problem: Problem) -> dict[str, Any]:
        print("Selected executor: qbraid")
        problem_data = problem.build_problem_data()

        if len(self.strategies) < 2:
            raise ValueError("--qbraid-strategies must include at least two strategies.")
        if len(self.environments) < 2:
            raise ValueError("--qbraid-environments must include at least two environments.")

        strategies = self._strategy_catalog(list(self.strategies))
        environments = [self._build_environment(name) for name in self.environments]

        runs: list[BenchmarkRun] = []
        for strategy in strategies:
            for environment in environments:
                print(
                    f"Running strategy='{strategy.name}' on environment='{environment.name}'"
                )
                run = self._run_single(
                    problem=problem,
                    problem_data=problem_data,
                    strategy=strategy,
                    environment=environment,
                )
                runs.append(run)
                print(
                    "  "
                    f"cut={run.cut_size} loss={run.final_loss:.6f} "
                    f"depth={run.metrics.depth} twoq={run.metrics.two_qubit_ops} "
                    f"cost={run.compiled_resource_cost:.3f} tradeoff={run.tradeoff_score:.5f}"
                )

        best_by_quality = max(runs, key=lambda run: run.quality_score)
        best_by_cost = min(runs, key=lambda run: run.compiled_resource_cost)
        best_by_tradeoff = max(runs, key=lambda run: run.tradeoff_score)

        print("=" * 70)
        print("QBRAID COMPILATION TRADEOFF SUMMARY")
        print("=" * 70)
        print(
            f"Best output quality:      {best_by_quality.strategy}/{best_by_quality.environment} "
            f"(quality={best_by_quality.quality_score:.4f})"
        )
        print(
            f"Lowest resource cost:     {best_by_cost.strategy}/{best_by_cost.environment} "
            f"(cost={best_by_cost.compiled_resource_cost:.4f})"
        )
        print(
            f"Best quality/cost tradeoff: {best_by_tradeoff.strategy}/{best_by_tradeoff.environment} "
            f"(score={best_by_tradeoff.tradeoff_score:.6f})"
        )
        print("=" * 70)

        return {
            "executor": "qbraid",
            "runs": [
                {
                    "strategy": run.strategy,
                    "environment": run.environment,
                    "qbraid_used": run.qbraid_used,
                    "final_loss": run.final_loss,
                    "cut_size": run.cut_size,
                    "quality_score": run.quality_score,
                    "compiled_resource_cost": run.compiled_resource_cost,
                    "tradeoff_score": run.tradeoff_score,
                    "metrics": {
                        "depth": run.metrics.depth,
                        "size": run.metrics.size,
                        "two_qubit_ops": run.metrics.two_qubit_ops,
                        "transpile_time": run.metrics.transpile_time,
                    },
                }
                for run in runs
            ],
            "best_by_quality": {
                "strategy": best_by_quality.strategy,
                "environment": best_by_quality.environment,
                "quality_score": best_by_quality.quality_score,
            },
            "best_by_cost": {
                "strategy": best_by_cost.strategy,
                "environment": best_by_cost.environment,
                "compiled_resource_cost": best_by_cost.compiled_resource_cost,
            },
            "best_by_tradeoff": {
                "strategy": best_by_tradeoff.strategy,
                "environment": best_by_tradeoff.environment,
                "tradeoff_score": best_by_tradeoff.tradeoff_score,
            },
        }






