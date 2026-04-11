from dataclasses import dataclass
import logging
import os
from pathlib import Path
from time import sleep, time
from typing import Any, Callable, Iterable, Self, cast

import numpy as np
from dotenv import load_dotenv
from qbraid.runtime import QbraidProvider
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.exceptions import RuntimeJobFailureError
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
    qbraid_device: Any | None = None


@dataclass(frozen=True)
class RuntimeMetrics:
    depth: int
    size: int
    two_qubit_ops: int
    transpile_time: float


@dataclass(frozen=True)
class QBraidExecutor(Executor):
    _RESULT_RETRY_ATTEMPTS = 3
    _RESULT_RETRY_BASE_DELAY_SECONDS = 2.0

    backend_name: str
    maxiter: int
    strategy: str
    environment: str
    qbraid_shots: int

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
            choices=("hardware", "aer", "clifford", "cloud"),
            default="aer",
            help="Execution environment for a single qBraid run.",
        )
        parser.add_argument(
            "--qbraid-shots",
            type=int,
            default=2048,
            help="Number of shots per circuit evaluation in qBraid cloud mode.",
        )

    @classmethod
    def from_namespace(cls, args) -> Self:
        return cls(
            backend_name=args.backend,
            maxiter=args.maxiter,
            strategy=args.qbraid_strategy,
            environment=args.qbraid_environment,
            qbraid_shots=args.qbraid_shots,
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
        if name == "cloud":
            load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
            api_key = os.getenv("QBRAID_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "qBraid cloud mode requires QBRAID_API_KEY in your environment or .env file."
                )
            try:
                provider = QbraidProvider(api_key=api_key)
                device = provider.get_device(self.backend_name)
            except Exception as exc:  # pragma: no cover - runtime environment dependent
                raise RuntimeError(
                    "Failed to initialize qBraid cloud device. Verify QBRAID_API_KEY and "
                    f"the device id passed via --backend (got '{self.backend_name}')."
                ) from exc

            logger.info("Using qBraid cloud device '%s'", self.backend_name)
            return ExecutionEnvironment(
                name="cloud",
                transpile_backend=None,
                estimator_mode=None,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
                qbraid_device=device,
            )

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
    def _build_basis_measurement_circuit(circuit, basis: str):
        measured = circuit.copy()
        for qubit in range(measured.num_qubits):
            if basis == "x":
                measured.h(qubit)
            elif basis == "y":
                measured.sdg(qubit)
                measured.h(qubit)
        measured.measure_all()
        return measured

    @staticmethod
    def _counts_expectation_for_op(op: Any, counts: dict[str, int]) -> float:
        terms = op.to_list()
        if not terms:
            return 0.0

        label, coeff = terms[0]
        active_qubits = [idx for idx, pauli in enumerate(reversed(label)) if pauli != "I"]
        total = sum(counts.values())
        if total <= 0:
            return 0.0

        expectation = 0.0
        for bitstring, count in counts.items():
            clean = bitstring.replace(" ", "")
            parity = 0
            for qubit in active_qubits:
                bit = clean[-1 - qubit]
                parity ^= int(bit)
            expectation += (-1.0 if parity else 1.0) * float(count)

        expectation /= float(total)
        return float(np.real(coeff)) * expectation

    @classmethod
    def _make_qbraid_cloud_evaluator(
        cls,
        *,
        device: Any,
        ansatz,
        observables: list[list[Any]],
        parameter_transform: Callable[[np.ndarray], np.ndarray],
        shots: int,
    ) -> ParameterEvaluator:
        def evaluate(params: np.ndarray) -> dict[int, float]:
            transformed = parameter_transform(np.asarray(params, dtype=float))
            bound = ansatz.assign_parameters(transformed, inplace=False)
            counts_by_basis: dict[str, dict[str, int]] = {}

            for basis in ("x", "y", "z"):
                measured = cls._build_basis_measurement_circuit(bound, basis)
                job = device.run(measured, shots=shots)
                result = job.result()
                counts_raw = result.data.get_counts()
                if isinstance(counts_raw, list):
                    counts = counts_raw[0] if counts_raw else {}
                else:
                    counts = counts_raw
                counts_by_basis[basis] = {str(k): int(v) for k, v in counts.items()}

            node_exp_map: dict[int, float] = {}
            idx = 0
            for basis, grouped_ops in zip(("x", "y", "z"), observables, strict=False):
                basis_counts = counts_by_basis[basis]
                for op in grouped_ops:
                    node_exp_map[idx] = cls._counts_expectation_for_op(op, basis_counts)
                    idx += 1
            return node_exp_map

        return evaluate

    @staticmethod
    def _make_evaluator(
        *,
        estimator: Estimator,
        ansatz,
        observables: list[list[Any]],
        parameter_transform: Callable[[np.ndarray], np.ndarray],
        logger: logging.Logger,
    ) -> ParameterEvaluator:
        def is_retryable_runtime_error(exc: Exception) -> bool:
            if isinstance(exc, RuntimeJobFailureError):
                message = str(exc).lower()
                return "error code 8057" in message or "control instrument error" in message

            exc_name = exc.__class__.__name__.lower()
            if "timeout" in exc_name:
                return True

            message = str(exc).lower()
            return "timed out" in message or "temporar" in message

        def run_with_retry(pubs: list[tuple[Any, list[Any], np.ndarray]]):
            attempts = QBraidExecutor._RESULT_RETRY_ATTEMPTS
            for attempt in range(1, attempts + 1):
                try:
                    job = estimator.run(pubs)  # type: ignore[arg-type]
                    return job.result()
                except Exception as exc:
                    if attempt >= attempts or not is_retryable_runtime_error(exc):
                        raise

                    delay = QBraidExecutor._RESULT_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "Estimator job failed with retryable runtime error (%s). "
                        "Retrying in %.1fs (%d/%d)",
                        exc,
                        delay,
                        attempt,
                        attempts,
                    )
                    sleep(delay)

        def evaluate(params: np.ndarray) -> dict[int, float]:
            transformed = parameter_transform(np.asarray(params, dtype=float))
            pubs = [
                (ansatz, observables[0], transformed),
                (ansatz, observables[1], transformed),
                (ansatz, observables[2], transformed),
            ]
            result = run_with_retry(pubs)
            if result is None:
                raise RuntimeError("Estimator returned no result payload.")
            result_iter = cast(Iterable[Any], result)

            node_exp_map = {}
            idx = 0
            for entry in result_iter:
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
    def _quality_score(metric_value: float | None, final_loss: float) -> float:
        if metric_value is not None:
            return float(metric_value)
        return -float(final_loss)

    @staticmethod
    def _resolve_primary_metric_from_candidates(
        postprocess: dict[str, Any], candidates: tuple[str, ...]
    ) -> tuple[str, Any | None]:
        metric_name = postprocess.get("primary_metric_name")
        metric_value = postprocess.get("primary_metric_value")
        if metric_name is not None and metric_value is not None:
            return str(metric_name), metric_value

        for candidate in candidates:
            if candidate in postprocess:
                return candidate, postprocess[candidate]

        for key, value in postprocess.items():
            if isinstance(value, (int, float)):
                return key, value

        return "primary_metric", None

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
        if environment.name == "cloud":
            compiled = ansatz
            qbraid_used = True
            transpile_time = 0.0
            logger.info("Cloud mode uses qBraid device-side compilation/routing")
        else:
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

        observables = problem.build_observables(getattr(compiled, "layout", None), problem_data)
        experiment_results: list[dict[str, Any]] = []
        iteration_times: list[float] = []
        if environment.name == "cloud":
            if environment.qbraid_device is None:
                raise RuntimeError("qBraid cloud environment is missing a runtime device.")
            evaluator = self._make_qbraid_cloud_evaluator(
                device=environment.qbraid_device,
                ansatz=compiled,
                observables=observables,
                parameter_transform=environment.parameter_transform,
                shots=self.qbraid_shots,
            )
        else:
            estimator = Estimator(mode=environment.estimator_mode)
            evaluator = self._make_evaluator(
                estimator=estimator,
                ansatz=compiled,
                observables=observables,
                parameter_transform=environment.parameter_transform,
                logger=logger,
            )
        loss_func = problem.make_loss(
            problem_data=problem_data,
            evaluator=evaluator,
            experiment_results=experiment_results,
            iteration_times=iteration_times,
            logger=logger,
        )
        objective: Callable[..., Any] = loss_func

        seed = getattr(problem_data, "seed", 42)
        rng = np.random.default_rng(seed)
        num_parameters = int(compiled.num_parameters)
        initial_params = rng.random(num_parameters)
        optimizer = problem.optimizer_config(num_parameters=num_parameters, maxiter=self.maxiter)
        logger.info("Optimize using %s options=%s", optimizer.method, optimizer.options)

        minimize_fn: Callable[..., Any] = cast(Any, minimize)
        optimization_result = minimize_fn(
            fun=cast(Any, objective),
            x0=cast(Any, initial_params),
            method=optimizer.method,
            options=optimizer.options,
        )
        logger.info(
            "Optimized parameters %s",
            problem.describe_parameters(np.asarray(optimization_result.x)),
        )

        postprocess = problem.postprocess(
            problem_data=problem_data, experiment_results=experiment_results
        )
        final_loss = (
            float(experiment_results[-1]["loss"]) if experiment_results else float("inf")
        )
        primary_metric_name, primary_metric_value = self._resolve_primary_metric_from_candidates(
            postprocess, problem.metric_candidates()
        )
        raw_cut_size = postprocess.get("cut_size")
        cut_size = int(raw_cut_size) if isinstance(raw_cut_size, int) else None
        metric_value = (
            float(primary_metric_value)
            if isinstance(primary_metric_value, (int, float))
            else float(cut_size)
            if cut_size is not None
            else None
        )
        quality_score = self._quality_score(metric_value=metric_value, final_loss=final_loss)
        compiled_resource_cost = self._calc_compiled_resource_cost(metrics)
        tradeoff_score = quality_score / max(compiled_resource_cost, 1e-9)
        logger.info(
            "Run complete: %s=%s final_loss=%.6f cost=%.3f tradeoff=%.5f",
            primary_metric_name,
            primary_metric_value,
            final_loss,
            compiled_resource_cost,
            tradeoff_score,
        )

        logger.info(
            "Summary %s=%s loss=%.6f depth=%s twoq=%s cost=%.3f tradeoff=%.5f",
            primary_metric_name,
            primary_metric_value,
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
            "qbraid_shots": self.qbraid_shots if environment.name == "cloud" else None,
            "primary_metric_name": primary_metric_name,
            "primary_metric_value": primary_metric_value,
            "optimizer_method": optimizer.method,
            "optimizer_options": dict(optimizer.options),
            "optimization_result": optimization_result,
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




