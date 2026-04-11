from dataclasses import dataclass
import logging
from pathlib import Path
from time import time
from typing import Any, Callable, Self, cast

import numpy as np
from dotenv import load_dotenv
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime import QiskitRuntimeService
from scipy.optimize import minimize

from executors.base import Executor, get_executor_logger
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
class QBraidExecutor(Executor):
    backend_name: str
    maxiter: int
    strategy: str
    environment: str

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        parser.add_argument(
            "--qbraid-strategy",
            choices=("balanced", "aggressive"),
            default="balanced",
            help="qBraid compilation strategy for a single run.",
        )
        parser.add_argument(
            "--qbraid-environment",
            choices=("hardware", "aer", "clifford"),
            default="aer",
            help="Execution environment for a single qBraid run.",
        )

    @classmethod
    def from_namespace(cls, args) -> Self:
        return cls(
            backend_name=args.backend,
            maxiter=args.maxiter,
            strategy=args.qbraid_strategy,
            environment=args.qbraid_environment,
        )

    @property
    def run_label(self) -> str:
        return (
            "qbraid("
            f"strategy={self.strategy}, "
            f"environment={self.environment}, "
            f"backend={self.backend_name}"
            ")"
        )

    @property
    def logger_name(self) -> str:
        return f"ex.qb.{self.strategy}.{self.environment}.{self.backend_name}"

    def _logger(self) -> logging.Logger:
        return get_executor_logger(self.logger_name)

    @property
    def benchmark_topics(self) -> set[str]:
        return {"quality_score", "compiled_resource_cost", "tradeoff_score"}

    @staticmethod
    def _snap_to_clifford_angles(params: np.ndarray) -> np.ndarray:
        params = np.asarray(params, dtype=float)
        step = np.pi / 2
        return np.round(params / step) * step

    def _build_environment(self, name: str) -> ExecutionEnvironment:
        logger = self._logger()
        if name == "hardware":
            load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
            try:
                service = QiskitRuntimeService()
                backend = service.backend(self.backend_name)
            except Exception as exc:  # pragma: no cover - runtime environment dependent
                raise RuntimeError(
                    "IBM Runtime service initialization failed for qBraid hardware mode. "
                    "Set up your IBM Quantum credentials before using hardware."
                ) from exc

            logger.info("Using IBM hardware backend environment")
            return ExecutionEnvironment(
                name="hardware",
                transpile_backend=backend,
                estimator_mode=backend,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
            )

        if name == "aer":
            load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
            try:
                service = QiskitRuntimeService()
                backend = service.backend(self.backend_name)
                simulator = AerSimulator.from_backend(backend)
                logger.info("Using Aer simulator seeded from IBM backend")
            except Exception:
                simulator = AerSimulator()
                logger.warning(
                    "IBM backend unavailable for Aer seeding; using default local Aer simulator"
                )
            return ExecutionEnvironment(
                name="aer",
                transpile_backend=simulator,
                estimator_mode=simulator,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
            )

        simulator = AerSimulator(method="stabilizer")  # type: ignore[arg-type]
        logger.info("Using local Clifford stabilizer simulation environment")
        return ExecutionEnvironment(
            name="clifford",
            transpile_backend=simulator,
            estimator_mode=simulator,
            parameter_transform=self._snap_to_clifford_angles,
        )

    @staticmethod
    def _strategy_by_name(name: str) -> CompilationStrategy:
        mapping = {
            "balanced": CompilationStrategy(
                name="balanced", optimization_level=1, routing_method="sabre"
            ),
            "aggressive": CompilationStrategy(
                name="aggressive", optimization_level=3, routing_method="sabre"
            ),
        }
        return mapping[name]

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
        return -float(final_loss)

    @staticmethod
    def _compile_with_qbraid_or_qiskit(
        *,
        circuit,
        strategy: CompilationStrategy,
        transpile_backend: Any,
        logger: logging.Logger,
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
            logger.info("Compiled circuit with qBraid transpiler")
        except Exception:
            pm_options: dict[str, Any] = {
                "backend": transpile_backend,
                "optimization_level": strategy.optimization_level,
            }
            if strategy.routing_method is not None:
                pm_options["routing_method"] = strategy.routing_method
            pm = generate_preset_pass_manager(**pm_options)
            compiled = pm.run(circuit)
            logger.warning("qBraid transpilation unavailable; fell back to Qiskit transpilation")

        return compiled, qbraid_used, time() - start

    def execute(self, problem: Problem) -> dict[str, Any]:
        logger = self._logger()
        logger.info("Start %s", self.run_label)
        problem_data = problem.build_problem_data(logger=logger)
        strategy = self._strategy_by_name(self.strategy)
        environment = self._build_environment(self.environment)

        ansatz = problem.build_ansatz(logger=logger)
        compiled, qbraid_used, transpile_time = self._compile_with_qbraid_or_qiskit(
            circuit=ansatz,
            strategy=strategy,
            transpile_backend=environment.transpile_backend,
            logger=logger,
        )
        logger.debug(
            "Circuit compiled: strategy=%s environment=%s depth=%s size=%s two_qubit_ops=%s",
            strategy.name,
            environment.name,
            compiled.depth(),
            compiled.size(),
            compiled.num_nonlocal_gates(),
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
            logger=logger,
        )
        objective: Callable[..., Any] = loss_func

        seed = getattr(problem_data, "seed", 42)
        rng = np.random.default_rng(seed)
        num_parameters = int(compiled.num_parameters)
        initial_params = rng.random(num_parameters)
        maxiter = max(self.maxiter, num_parameters + 2)

        minimize_fn: Callable[..., Any] = cast(Any, minimize)
        _ = minimize_fn(
            fun=cast(Any, objective),
            x0=cast(Any, initial_params),
            method="COBYLA",
            options={"maxiter": maxiter},
        )

        postprocess = problem.postprocess(
            problem_data=problem_data, experiment_results=experiment_results
        )
        final_loss = (
            float(experiment_results[-1]["loss"]) if experiment_results else float("inf")
        )
        raw_cut_size = postprocess.get("cut_size")
        cut_size = int(raw_cut_size) if isinstance(raw_cut_size, int) else None

        quality_score = self._quality_score(cut_size=cut_size, final_loss=final_loss)
        compiled_resource_cost = self._calc_compiled_resource_cost(metrics)
        tradeoff_score = quality_score / max(compiled_resource_cost, 1e-9)
        logger.info(
            "Run complete: cut_size=%s final_loss=%.6f cost=%.3f tradeoff=%.5f",
            cut_size,
            final_loss,
            compiled_resource_cost,
            tradeoff_score,
        )

        logger.info(
            "Summary cut=%s loss=%.6f depth=%s twoq=%s cost=%.3f tradeoff=%.5f",
            cut_size,
            final_loss,
            metrics.depth,
            metrics.two_qubit_ops,
            compiled_resource_cost,
            tradeoff_score,
        )

        return {
            "executor": "qbraid",
            "run_label": self.run_label,
            "benchmark_topics": sorted(self.benchmark_topics),
            "qbraid_used": qbraid_used,
            "strategy": strategy.name,
            "environment": environment.name,
            "final_loss": final_loss,
            "cut_size": cut_size,
            "quality_score": quality_score,
            "compiled_resource_cost": compiled_resource_cost,
            "tradeoff_score": tradeoff_score,
            "metrics": {
                "depth": metrics.depth,
                "size": metrics.size,
                "two_qubit_ops": metrics.two_qubit_ops,
                "transpile_time": metrics.transpile_time,
            },
            "postprocess": postprocess,
            "experiment_results": experiment_results,
        }




