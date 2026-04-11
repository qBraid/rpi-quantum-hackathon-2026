from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass

import numpy as np

QISKIT_AVAILABLE = importlib.util.find_spec("qiskit") is not None
AER_AVAILABLE = importlib.util.find_spec("qiskit_aer") is not None


@dataclass
class QAOAProblem:
    weights: list[float]
    pair_penalties: dict[tuple[int, int], float]
    budget: int


def bitstrings(num_qubits: int) -> list[tuple[int, ...]]:
    return [tuple((idx >> bit) & 1 for bit in range(num_qubits)) for idx in range(2**num_qubits)]


def cost_of(problem: QAOAProblem, bits: tuple[int, ...]) -> float:
    weight_term = sum(weight * bit for weight, bit in zip(problem.weights, bits, strict=True))
    pair_term = sum(problem.pair_penalties[pair] * bits[pair[0]] * bits[pair[1]] for pair in problem.pair_penalties)
    budget_penalty = 0.7 * (sum(bits) - problem.budget) ** 2
    return weight_term - pair_term - budget_penalty


def brute_force_best(problem: QAOAProblem) -> tuple[tuple[int, ...], float]:
    evaluated = [(bits, cost_of(problem, bits)) for bits in bitstrings(len(problem.weights))]
    return max(evaluated, key=lambda item: item[1])


def brute_force_worst(problem: QAOAProblem) -> tuple[tuple[int, ...], float]:
    evaluated = [(bits, cost_of(problem, bits)) for bits in bitstrings(len(problem.weights))]
    return min(evaluated, key=lambda item: item[1])


def qaoa_level1(problem: QAOAProblem) -> dict:
    num_qubits = len(problem.weights)
    states = bitstrings(num_qubits)
    basis_costs = np.array([cost_of(problem, state) for state in states], dtype=float)
    best_bits, best_cost = brute_force_best(problem)
    uniform = np.ones(2**num_qubits, dtype=complex) / math.sqrt(2**num_qubits)
    best_result = None

    for gamma in np.linspace(0.1, 1.2, 12):
        phased = uniform * np.exp(-1j * gamma * basis_costs)
        for beta in np.linspace(0.1, 1.2, 12):
            mixer = np.array(
                [[math.cos(beta), -1j * math.sin(beta)], [-1j * math.sin(beta), math.cos(beta)]],
                dtype=complex,
            )
            full_mixer = np.array([[1]], dtype=complex)
            for _ in range(num_qubits):
                full_mixer = np.kron(full_mixer, mixer)
            mixed = full_mixer @ phased
            probabilities = np.abs(mixed) ** 2
            expected_cost = float(np.dot(probabilities, basis_costs))
            success_probability = float(
                sum(probabilities[index] for index, bits in enumerate(states) if bits == best_bits)
            )
            candidate = {
                "beta": round(float(beta), 4),
                "gamma": round(float(gamma), 4),
                "expected_cost": round(expected_cost, 4),
                "success_probability": round(success_probability, 4),
                "best_bitstring": list(best_bits),
                "best_cost": round(float(best_cost), 4),
            }
            if best_result is None or candidate["expected_cost"] > best_result["expected_cost"]:
                best_result = candidate

    assert best_result is not None
    return best_result


def approximation_ratio(problem: QAOAProblem, observed_cost: float) -> float:
    _, optimum = brute_force_best(problem)
    _, worst = brute_force_worst(problem)
    span = optimum - worst
    if span == 0:
        return 1.0
    normalized = (observed_cost - worst) / span
    return round(float(max(0.0, min(1.0, normalized))), 4)


def circuit_metrics(circuit) -> dict:
    gate_breakdown = {str(key): int(value) for key, value in dict(circuit.count_ops()).items()}
    two_qubit_gate_count = sum(gate_breakdown.get(name, 0) for name in ("cx", "cz", "ecr"))
    total_gates = sum(gate_breakdown.values())
    return {
        "depth": int(circuit.depth() or 0),
        "width": int(circuit.num_qubits),
        "two_qubit_gate_count": int(two_qubit_gate_count),
        "total_gates": int(total_gates),
        "gate_breakdown": gate_breakdown,
    }


def build_qaoa_circuit(problem: QAOAProblem, gamma: float, beta: float):
    if not QISKIT_AVAILABLE:
        raise RuntimeError("Qiskit is not installed")

    from qiskit import QuantumCircuit

    num_qubits = len(problem.weights)
    circuit = QuantumCircuit(num_qubits, num_qubits)

    for qubit in range(num_qubits):
        circuit.h(qubit)

    for qubit, weight in enumerate(problem.weights):
        circuit.rz(2 * gamma * weight, qubit)

    for (control, target), penalty in problem.pair_penalties.items():
        circuit.cx(control, target)
        circuit.rz(2 * gamma * penalty, target)
        circuit.cx(control, target)

    budget_gamma = gamma * 0.7
    for qubit in range(num_qubits):
        circuit.rz(2 * budget_gamma * (1 - 2 * problem.budget / max(1, num_qubits)), qubit)
    for left in range(num_qubits):
        for right in range(left + 1, num_qubits):
            circuit.cx(left, right)
            circuit.rz(2 * budget_gamma / max(1, num_qubits), right)
            circuit.cx(left, right)

    for qubit in range(num_qubits):
        circuit.rx(2 * beta, qubit)

    circuit.measure(range(num_qubits), range(num_qubits))
    return circuit


def parse_counts(problem: QAOAProblem, counts: dict[str, int]) -> tuple[dict[str, dict], float, float]:
    exact_bits, _ = brute_force_best(problem)
    total = max(1, sum(counts.values()))
    parsed: dict[str, dict] = {}
    expected_cost = 0.0
    success_probability = 0.0

    for raw_bits, count in counts.items():
        bits = tuple(int(bit) for bit in reversed(raw_bits.zfill(len(problem.weights))))
        cost = cost_of(problem, bits)
        probability = count / total
        parsed[raw_bits] = {
            "bits": list(bits),
            "count": int(count),
            "probability": round(probability, 6),
            "cost": round(float(cost), 4),
        }
        expected_cost += probability * cost
        if bits == exact_bits:
            success_probability += probability

    return parsed, round(expected_cost, 4), round(success_probability, 4)


def _noise_model():
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(depolarizing_error(0.001, 1), ["rz", "sx", "x", "h", "rx"])
    noise_model.add_all_qubit_quantum_error(depolarizing_error(0.01, 2), ["cx", "cz", "ecr"])
    return noise_model


def run_transpiled_qaoa(problem: QAOAProblem, circuit, shots: int) -> dict:
    if not AER_AVAILABLE:
        raise RuntimeError("qiskit-aer is not installed")

    from qiskit_aer import AerSimulator

    ideal_backend = AerSimulator(method="automatic")
    ideal_counts = ideal_backend.run(circuit, shots=shots).result().get_counts()

    noisy_backend = AerSimulator(method="density_matrix")
    noisy_counts = noisy_backend.run(circuit, shots=shots, noise_model=_noise_model()).result().get_counts()

    ideal_parsed, ideal_expected, ideal_success = parse_counts(problem, ideal_counts)
    noisy_parsed, noisy_expected, noisy_success = parse_counts(problem, noisy_counts)
    return {
        "ideal_simulator": {
            "counts": ideal_parsed,
            "expected_cost": ideal_expected,
            "success_probability": ideal_success,
            "approximation_ratio": approximation_ratio(problem, ideal_expected),
            "unique_outcomes": len(ideal_parsed),
        },
        "noisy_simulator": {
            "counts": noisy_parsed,
            "expected_cost": noisy_expected,
            "success_probability": noisy_success,
            "approximation_ratio": approximation_ratio(problem, noisy_expected),
            "unique_outcomes": len(noisy_parsed),
            "noise_model": "depolarizing (1Q 0.1%, 2Q 1.0%)",
        },
    }
