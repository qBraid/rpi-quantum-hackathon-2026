from dataclasses import dataclass
import logging
from pathlib import Path
from time import time
from typing import Any, Callable, Self, cast

import numpy as np
from dotenv import load_dotenv
from scipy.optimize import minimize
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime import QiskitRuntimeService

from executors.base import Executor, get_executor_logger
from problems.base import ParameterEvaluator, Problem


@dataclass(frozen=True)
class RuntimeBundle:
    label: str
    transpile_backend: Any
    estimator_mode: Any
    parameter_transform: Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class QiskitExecutor(Executor):
    mode: str
    backend_name: str
    maxiter: int

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        parser.add_argument(
            "--mode",
            choices=("hardware", "aer", "clifford"),
            default="aer",
            help="Choose the execution mode.",
        )
        parser.add_argument(
            "--backend",
            default="ibm_rensselaer",
            help=(
                "Backend identifier: IBM backend name for Qiskit hardware/Aer modes, "
                "or qBraid device id when using qBraid cloud mode."
            ),
        )
        parser.add_argument(
            "--maxiter",
            type=int,
            default=10,
            help="Maximum number of COBYLA iterations.",
        )

    @classmethod
    def from_namespace(cls, args) -> Self:
        return cls(mode=args.mode, backend_name=args.backend, maxiter=args.maxiter)

    @property
    def run_label(self) -> str:
        return f"qiskit(mode={self.mode}, backend={self.backend_name})"

    @property
    def logger_name(self) -> str:
        return f"ex.qk.{self.mode}.{self.backend_name}"

    def _logger(self) -> logging.Logger:
        return get_executor_logger(self.logger_name)

    @property
    def benchmark_topics(self) -> set[str]:
        # Legacy executor path does not provide normalized benchmark metrics.
        return set()

    @staticmethod
    def _snap_to_clifford_angles(params: np.ndarray) -> np.ndarray:
        params = np.asarray(params, dtype=float)
        step = np.pi / 2
        return np.round(params / step) * step

    def _build_runtime(self) -> RuntimeBundle:
        logger = self._logger()
        if self.mode in {"hardware", "aer"}:
            load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")
            try:
                service = QiskitRuntimeService()
            except Exception as exc:  # pragma: no cover - runtime environment dependent
                raise RuntimeError(
                    "IBM Runtime service initialization failed. Set up your IBM Quantum "
                    "credentials before using hardware or Aer-from-hardware mode."
                ) from exc

            backend = service.backend(self.backend_name)
            if self.mode == "hardware":
                logger.info("Using IBM hardware backend runtime mode")
                return RuntimeBundle(
                    label=f"IBM hardware backend '{self.backend_name}'",
                    transpile_backend=backend,
                    estimator_mode=backend,
                    parameter_transform=lambda params: np.asarray(params, dtype=float),
                )

            simulator = AerSimulator.from_backend(backend)
            logger.info("Using Aer simulator seeded from IBM backend")
            return RuntimeBundle(
                label=f"Aer simulator seeded from '{self.backend_name}'",
                transpile_backend=simulator,
                estimator_mode=simulator,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
            )

        simulator = AerSimulator(method="stabilizer")  # type: ignore[arg-type]
        logger.info("Using local Clifford stabilizer simulation runtime mode")
        return RuntimeBundle(
            label="Clifford stabilizer simulation",
            transpile_backend=simulator,
            estimator_mode=simulator,
            parameter_transform=self._snap_to_clifford_angles,
        )

    @staticmethod
    def _make_evaluator(
        *,
        estimator: Estimator,
        ansatz,
        observables: list[list[Any]],
        runtime: RuntimeBundle,
    ) -> ParameterEvaluator:
        def evaluate(params: np.ndarray) -> dict[int, float]:
            transformed = runtime.parameter_transform(np.asarray(params, dtype=float))
            pubs = [
                (ansatz, observables[0], transformed),
                (ansatz, observables[1], transformed),
                (ansatz, observables[2], transformed),
            ]
            job = estimator.run(pubs)  # type: ignore[arg-type]
            result = job.result()

            node_exp_map = {}
            idx = 0
            for r in result:
                for ev in r.data.evs:
                    node_exp_map[idx] = ev
                    idx += 1
            return node_exp_map

        return evaluate

    @staticmethod
    def _resolve_primary_metric_from_candidates(
        postprocess: dict[str, Any], candidates: tuple[str, ...]
    ) -> tuple[str, Any]:
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

    def execute(self, problem: Problem) -> dict[str, Any]:
        logger = self._logger()
        logger.info("Start mode=%s", self.mode)
        start_setup = time()
        runtime = self._build_runtime()
        setup_time = time() - start_setup
        logger.info("Setup %.4fs (%s)", setup_time, runtime.label)

        problem_data = problem.build_problem_data(logger=logger)

        logger.info("Build and optimize circuit")
        start_circuit = time()
        ansatz = problem.build_ansatz(logger=logger)
        pm = generate_preset_pass_manager(
            backend=runtime.transpile_backend, optimization_level=3
        )
        qc_optimized = pm.run(ansatz)
        logger.debug(
            "Circuit transpiled: qubits=%s params=%s depth=%s",
            qc_optimized.num_qubits,
            qc_optimized.num_parameters,
            qc_optimized.depth(),
        )
        logger.info(
            "Optimized circuit qubits=%s params=%s depth=%s",
            qc_optimized.num_qubits,
            qc_optimized.num_parameters,
            qc_optimized.depth(),
        )
        circuit_time = time() - start_circuit
        logger.info("Circuit optimization %.4fs", circuit_time)

        observables = problem.build_observables(qc_optimized.layout, problem_data)
        estimator = Estimator(mode=runtime.estimator_mode)
        experiment_results: list[dict[str, Any]] = []
        iteration_times: list[float] = []
        loss_func = problem.make_loss(
            problem_data=problem_data,
            evaluator=self._make_evaluator(
                estimator=estimator,
                ansatz=qc_optimized,
                observables=observables,
                runtime=runtime,
            ),
            experiment_results=experiment_results,
            iteration_times=iteration_times,
            logger=logger,
        )

        seed = getattr(problem_data, "seed", 42)
        rng = np.random.default_rng(seed)
        num_parameters = int(qc_optimized.num_parameters)
        initial_params = rng.random(num_parameters)

        optimizer = problem.optimizer_config(num_parameters=num_parameters, maxiter=self.maxiter)
        logger.info("Optimize on %s using %s", runtime.label, optimizer.method)

        start_optimization = time()
        objective: Callable[..., Any] = loss_func
        minimize_fn: Callable[..., Any] = cast(Any, minimize)
        # noinspection PyTypeChecker
        result = minimize_fn(
            fun=cast(Any, objective),
            x0=cast(Any, initial_params),
            method=optimizer.method,
            options=optimizer.options,
        )
        optimization_time = time() - start_optimization
        logger.info("Optimization %.4fs", optimization_time)
        logger.info("Optimizer method=%s options=%s", optimizer.method, optimizer.options)
        logger.info("Optimized parameters %s", problem.describe_parameters(np.asarray(result.x)))

        postprocess = problem.postprocess(
            problem_data=problem_data, experiment_results=experiment_results
        )
        primary_metric_name, primary_metric_value = self._resolve_primary_metric_from_candidates(
            postprocess, problem.metric_candidates()
        )
        logger.info(
            "Result %s=%s objective=%s",
            primary_metric_name,
            primary_metric_value,
            result.fun,
        )

        average_iteration_time = float(np.mean(iteration_times)) if iteration_times else 0.0
        min_iteration_time = float(np.min(iteration_times)) if iteration_times else 0.0
        max_iteration_time = float(np.max(iteration_times)) if iteration_times else 0.0

        logger.info(
            "Timing setup=%.4fs problem=%.4fs circuit=%.4fs optimize=%.4fs iter(avg/min/max)=%.4f/%.4f/%.4f total=%.4fs",
            setup_time,
            problem_data.setup_time,
            circuit_time,
            optimization_time,
            average_iteration_time,
            min_iteration_time,
            max_iteration_time,
            setup_time + problem_data.setup_time + circuit_time + optimization_time,
        )

        return {
            "executor": "qiskit",
            "run_label": self.run_label,
            "benchmark_topics": sorted(self.benchmark_topics),
            "runtime_label": runtime.label,
            "setup_time": setup_time,
            "problem_setup_time": problem_data.setup_time,
            "circuit_time": circuit_time,
            "optimization_time": optimization_time,
            "optimizer_method": optimizer.method,
            "optimizer_options": dict(optimizer.options),
            "primary_metric_name": primary_metric_name,
            "primary_metric_value": primary_metric_value,
            "cut_size": postprocess.get("cut_size"),
            "optimization_result": result,
            "postprocess": postprocess,
            "experiment_results": experiment_results,
        }
