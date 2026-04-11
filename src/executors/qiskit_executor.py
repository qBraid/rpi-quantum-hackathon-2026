from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any, Callable, Self

import numpy as np
from dotenv import load_dotenv
from scipy.optimize import minimize
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit_ibm_runtime import QiskitRuntimeService

from executors.base import Executor
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
            help="IBM backend name to use for hardware and Aer-from-hardware modes.",
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

    @staticmethod
    def _snap_to_clifford_angles(params: np.ndarray) -> np.ndarray:
        params = np.asarray(params, dtype=float)
        step = np.pi / 2
        return np.round(params / step) * step

    def _build_runtime(self) -> RuntimeBundle:
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
                return RuntimeBundle(
                    label=f"IBM hardware backend '{self.backend_name}'",
                    transpile_backend=backend,
                    estimator_mode=backend,
                    parameter_transform=lambda params: np.asarray(params, dtype=float),
                )

            simulator = AerSimulator.from_backend(backend)
            return RuntimeBundle(
                label=f"Aer simulator seeded from '{self.backend_name}'",
                transpile_backend=simulator,
                estimator_mode=simulator,
                parameter_transform=lambda params: np.asarray(params, dtype=float),
            )

        simulator = AerSimulator(method="stabilizer")  # type: ignore[arg-type]
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

    def execute(self, problem: Problem) -> dict[str, Any]:
        print(f"Selected mode: {self.mode}")
        start_setup = time()
        runtime = self._build_runtime()
        setup_time = time() - start_setup
        print(f"✓ Runtime setup completed in {setup_time:.4f}s ({runtime.label})\n")

        problem_data = problem.build_problem_data()

        print("Building and optimizing quantum circuit...")
        start_circuit = time()
        ansatz = problem.build_ansatz()
        pm = generate_preset_pass_manager(
            backend=runtime.transpile_backend, optimization_level=3
        )
        qc_optimized = pm.run(ansatz)
        print(
            f"Optimized circuit: {qc_optimized.num_qubits} qubits, "
            f"{qc_optimized.num_parameters} parameters, depth {qc_optimized.depth()}"
        )
        circuit_time = time() - start_circuit
        print(f"✓ Circuit optimization completed in {circuit_time:.4f}s\n")

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
        )

        seed = getattr(problem_data, "seed", 42)
        rng = np.random.default_rng(seed)
        initial_params = rng.random(qc_optimized.num_parameters)

        cobyla_miniter = qc_optimized.num_parameters + 2
        cobyla_maxiter = max(self.maxiter, cobyla_miniter)
        if cobyla_maxiter != self.maxiter:
            print(
                f"Requested COBYLA maxiter={self.maxiter} is below the solver minimum "
                f"for {qc_optimized.num_parameters} parameters; using {cobyla_maxiter} instead."
            )

        print(f"Starting optimization on {runtime.label}...")
        start_optimization = time()
        minimize_options: dict[str, int] = {"maxiter": cobyla_maxiter}
        result = minimize(
            loss_func,
            initial_params,
            method="COBYLA",
            options=minimize_options,
        )  # type: ignore[arg-type, call-overload]
        optimization_time = time() - start_optimization
        print(f"\n✓ Optimization completed in {optimization_time:.4f}s\n")

        postprocess = problem.postprocess(
            problem_data=problem_data, experiment_results=experiment_results
        )
        cut_size = postprocess["cut_size"]
        print(f"Final cut size: {cut_size}")
        print(f"Optimization result:\n{result}\n")

        average_iteration_time = float(np.mean(iteration_times)) if iteration_times else 0.0
        min_iteration_time = float(np.min(iteration_times)) if iteration_times else 0.0
        max_iteration_time = float(np.max(iteration_times)) if iteration_times else 0.0

        print("=" * 70)
        print("BENCHMARKING SUMMARY")
        print("=" * 70)
        print(f"Setup time (runtime creation):         {setup_time:10.4f}s")
        print(f"Problem setup time:                    {problem_data.setup_time:10.4f}s")
        print(f"Circuit setup & optimization time:     {circuit_time:10.4f}s")
        print(f"Optimization loop time:                {optimization_time:10.4f}s")
        print(f"  - Average time per iteration:        {average_iteration_time:10.4f}s")
        print(f"  - Min iteration time:                {min_iteration_time:10.4f}s")
        print(f"  - Max iteration time:                {max_iteration_time:10.4f}s")
        print(
            f"Total runtime:                         {setup_time + problem_data.setup_time + circuit_time + optimization_time:10.4f}s"
        )
        print("=" * 70)

        return {
            "runtime_label": runtime.label,
            "setup_time": setup_time,
            "problem_setup_time": problem_data.setup_time,
            "circuit_time": circuit_time,
            "optimization_time": optimization_time,
            "cut_size": cut_size,
            "optimization_result": result,
            "postprocess": postprocess,
            "experiment_results": experiment_results,
        }
