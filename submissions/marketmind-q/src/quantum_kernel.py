"""Manual quantum kernel machinery for Qiskit feature maps."""

from __future__ import annotations

import time
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class KernelResources:
    qubits: int
    kernel_circuit_depth: int
    kernel_two_qubit_gates: int
    shots: Optional[int]
    selected_features: tuple[str, ...] = ()


def _require_qiskit():
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit.circuit.library import zz_feature_map
        from qiskit.quantum_info import Statevector
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "Qiskit is required for quantum kernels. Install project requirements first."
        ) from exc
    return QuantumCircuit, transpile, zz_feature_map, Statevector


@lru_cache(maxsize=16)
def build_feature_map(feature_dim: int):
    _, _, zz_feature_map, _ = _require_qiskit()
    return zz_feature_map(feature_dimension=feature_dim, reps=2, entanglement="linear")


def bind_feature_map(feature_dim: int, values: np.ndarray):
    circuit = build_feature_map(feature_dim)
    params = sorted(circuit.parameters, key=lambda parameter: parameter.name)
    if len(params) != len(values):
        raise ValueError(f"Expected {len(params)} feature values, received {len(values)}.")
    return circuit.assign_parameters({param: float(value) for param, value in zip(params, values)}, inplace=False)


def statevectors(x: np.ndarray) -> np.ndarray:
    _, _, _, Statevector = _require_qiskit()
    vectors = []
    for row in x:
        bound = bind_feature_map(x.shape[1], row)
        vectors.append(Statevector.from_instruction(bound).data)
    return np.asarray(vectors)


def exact_kernel(x_left: np.ndarray, x_right: np.ndarray) -> np.ndarray:
    left_vectors = statevectors(x_left)
    right_vectors = statevectors(x_right)
    overlaps = left_vectors @ np.conjugate(right_vectors).T
    return np.abs(overlaps) ** 2


def exact_train_test_kernels(x_train: np.ndarray, x_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    train_vectors = statevectors(x_train)
    test_vectors = statevectors(x_test)
    train_overlaps = train_vectors @ np.conjugate(train_vectors).T
    test_overlaps = test_vectors @ np.conjugate(train_vectors).T
    return np.abs(train_overlaps) ** 2, np.abs(test_overlaps) ** 2


def make_compute_uncompute_circuit(x_values: np.ndarray, y_values: np.ndarray):
    QuantumCircuit, _, _, _ = _require_qiskit()
    feature_dim = len(x_values)
    circuit = QuantumCircuit(feature_dim)
    circuit.compose(bind_feature_map(feature_dim, x_values), inplace=True)
    circuit.compose(bind_feature_map(feature_dim, y_values).inverse(), inplace=True)
    circuit.measure_all()
    return circuit


def _noise_model():
    try:
        import qiskit_aer.noise as noise
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("qiskit-aer is required for noisy quantum kernels.") from exc

    noise_model = noise.NoiseModel()
    one_qubit = noise.depolarizing_error(0.001, 1)
    two_qubit = noise.depolarizing_error(0.01, 2)
    readout = noise.ReadoutError([[0.98, 0.02], [0.02, 0.98]])
    noise_model.add_all_qubit_quantum_error(one_qubit, ["h", "x", "sx", "rx", "ry", "rz", "p"])
    noise_model.add_all_qubit_quantum_error(two_qubit, ["cx", "cz"])
    noise_model.add_all_qubit_readout_error(readout)
    return noise_model


def shot_kernel(
    x_left: np.ndarray,
    x_right: np.ndarray,
    *,
    shots: int = 1024,
    noisy: bool = False,
    seed: int = 42,
) -> np.ndarray:
    if os.getenv("MARKETMIND_Q_USE_AER", "0") != "1":
        return finite_shot_kernel_from_exact(x_left, x_right, shots=shots, noisy=noisy, seed=seed)

    try:
        from qiskit import transpile
        from qiskit_aer import AerSimulator
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("qiskit-aer is required for shot-based quantum kernels.") from exc

    simulator = AerSimulator(
        noise_model=_noise_model() if noisy else None,
        seed_simulator=seed,
        max_parallel_threads=1,
        max_parallel_experiments=1,
        max_parallel_shots=1,
    )
    kernel = np.zeros((len(x_left), len(x_right)), dtype=float)
    zero_key = "0" * x_left.shape[1]
    for i, x_values in enumerate(x_left):
        circuits = [make_compute_uncompute_circuit(x_values, y_values) for y_values in x_right]
        transpiled = transpile(circuits, simulator, optimization_level=1)
        result = simulator.run(transpiled, shots=shots, seed_simulator=seed).result()
        for j, _ in enumerate(x_right):
            counts = result.get_counts(j)
            kernel[i, j] = counts.get(zero_key, 0) / shots
    return kernel


def finite_shot_kernel_from_exact(
    x_left: np.ndarray,
    x_right: np.ndarray,
    *,
    shots: int,
    noisy: bool,
    seed: int,
) -> np.ndarray:
    """Shot-limited fallback for environments where Aer cannot execute.

    Some sandboxed macOS environments can import qiskit-aer but crash when the
    simulator opens OpenMP shared memory. This fallback still uses Qiskit
    statevectors for the quantum feature map, then applies binomial shot noise.
    The noisy mode additionally attenuates fidelities toward the uniform
    zero-state probability as a conservative proxy for depolarizing/readout
    noise.
    """
    rng = np.random.default_rng(seed)
    probabilities = exact_kernel(x_left, x_right)
    if noisy:
        floor = 1.0 / (2 ** x_left.shape[1])
        probabilities = 0.94 * probabilities + 0.06 * floor
    sampled = rng.binomial(shots, np.clip(probabilities, 0.0, 1.0)) / shots
    return sampled


def sample_probabilities(
    train_probabilities: np.ndarray,
    test_probabilities: np.ndarray,
    *,
    feature_dim: int,
    shots: int,
    noisy: bool,
    seed: int,
) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    train_probs = np.asarray(train_probabilities, dtype=float)
    test_probs = np.asarray(test_probabilities, dtype=float)
    if noisy:
        floor = 1.0 / (2 ** feature_dim)
        train_probs = 0.94 * train_probs + 0.06 * floor
        test_probs = 0.94 * test_probs + 0.06 * floor
    train_sampled = rng.binomial(shots, np.clip(train_probs, 0.0, 1.0)) / shots
    test_sampled = rng.binomial(shots, np.clip(test_probs, 0.0, 1.0)) / shots
    return train_sampled, test_sampled


def postprocess_kernel(kernel: np.ndarray, *, train: bool) -> np.ndarray:
    processed = np.clip(np.asarray(kernel, dtype=float), 0.0, 1.0)
    if train:
        processed = (processed + processed.T) / 2.0
        np.fill_diagonal(processed, 1.0)
    return processed


def circuit_resources(feature_dim: int, *, shots: Optional[int], selected_features: tuple[str, ...] = ()) -> KernelResources:
    _, transpile, _, _ = _require_qiskit()
    values_x = np.linspace(0.2, 1.1, feature_dim, dtype=float)
    values_y = np.linspace(1.3, 0.4, feature_dim, dtype=float)
    base = make_compute_uncompute_circuit(values_x, values_y)
    compiled = transpile(base, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1)
    counts = compiled.count_ops()
    two_qubit = int(counts.get("cx", 0) + counts.get("cz", 0))
    return KernelResources(
        qubits=feature_dim,
        kernel_circuit_depth=int(compiled.depth()),
        kernel_two_qubit_gates=two_qubit,
        shots=shots,
        selected_features=selected_features,
    )


def compute_quantum_kernels(
    x_train: np.ndarray,
    x_test: np.ndarray,
    *,
    mode: str,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, KernelResources, float]:
    start = time.perf_counter()
    if mode == "statevector_exact":
        train_kernel = exact_kernel(x_train, x_train)
        test_kernel = exact_kernel(x_test, x_train)
        shots = None
    elif mode == "shots_1024":
        train_kernel = shot_kernel(x_train, x_train, shots=1024, noisy=False, seed=seed)
        test_kernel = shot_kernel(x_test, x_train, shots=1024, noisy=False, seed=seed)
        shots = 1024
    elif mode == "noisy_1024":
        train_kernel = shot_kernel(x_train, x_train, shots=1024, noisy=True, seed=seed)
        test_kernel = shot_kernel(x_test, x_train, shots=1024, noisy=True, seed=seed)
        shots = 1024
    else:
        raise ValueError(f"Unsupported quantum mode: {mode}")
    elapsed = time.perf_counter() - start
    resources = circuit_resources(x_train.shape[1], shots=shots)
    return postprocess_kernel(train_kernel, train=True), postprocess_kernel(test_kernel, train=False), resources, elapsed


def compute_quantum_kernel_bundle(
    x_train: np.ndarray,
    x_test: np.ndarray,
    *,
    modes: list[str],
    seed: int = 42,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, KernelResources, float]]:
    """Compute several quantum modes while reusing statevector fidelities."""
    if os.getenv("MARKETMIND_Q_USE_AER", "0") == "1":
        return {mode: compute_quantum_kernels(x_train, x_test, mode=mode, seed=seed) for mode in modes}

    start = time.perf_counter()
    exact_train, exact_test = exact_train_test_kernels(x_train, x_test)
    exact_seconds = time.perf_counter() - start
    results: Dict[str, Tuple[np.ndarray, np.ndarray, KernelResources, float]] = {}
    for offset, mode in enumerate(modes):
        if mode == "statevector_exact":
            train_kernel = exact_train.copy()
            test_kernel = exact_test.copy()
            shots = None
        elif mode == "shots_1024":
            train_kernel, test_kernel = sample_probabilities(
                exact_train,
                exact_test,
                feature_dim=x_train.shape[1],
                shots=1024,
                noisy=False,
                seed=seed + offset,
            )
            shots = 1024
        elif mode == "noisy_1024":
            train_kernel, test_kernel = sample_probabilities(
                exact_train,
                exact_test,
                feature_dim=x_train.shape[1],
                shots=1024,
                noisy=True,
                seed=seed + offset,
            )
            shots = 1024
        else:
            raise ValueError(f"Unsupported quantum mode: {mode}")
        resources = circuit_resources(x_train.shape[1], shots=shots)
        results[mode] = (
            postprocess_kernel(train_kernel, train=True),
            postprocess_kernel(test_kernel, train=False),
            resources,
            exact_seconds,
        )
    return results
