from itertools import combinations
import time

import matplotlib.pyplot as plt
import numpy as np
import rustworkx as rx
from scipy.optimize import minimize

from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.circuit.library import efficient_su2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2 as Estimator

# ============================================================================
# Setup: Create AER simulator from IBM Rensselaer backend configuration
# ============================================================================
print("Setting up AER simulator from IBM Rensselaer backend...")
start_setup = time.time()

service = QiskitRuntimeService()
real_backend = service.backend("ibm_rensselaer")
aer = AerSimulator.from_backend(real_backend)

setup_time = time.time() - start_setup
print(f"✓ Simulator setup completed in {setup_time:.4f}s\n")

# ============================================================================
# Step 1: Create MaxCut problem using Pauli Correlation Encoding
# ============================================================================
print("Creating MaxCut problem with Pauli Correlation Encoding...")
start_problem = time.time()

# Problem parameters
num_nodes = 100  # Smaller than notebook (1000) for faster demo on simulator
num_qubits = 10  # Number of qubits needed (approximately sqrt of nodes)
graph = rx.undirected_gnp_random_graph(num_nodes, 0.1, seed=42)

print(f"Graph: {num_nodes} nodes, {len(graph.edges())} edges")

# Helper function to calculate cut size
def calc_cut_size(graph, partition0, partition1):
    """Calculate the cut size of the given partitions of the graph."""
    cut_size = 0
    for edge0, edge1 in graph.edge_list():
        if edge0 in partition0 and edge1 in partition1:
            cut_size += 1
        elif edge0 in partition1 and edge1 in partition0:
            cut_size += 1
    return cut_size


# Divide nodes into three sets for X, Y, Z encoding
list_size = num_nodes // 3
node_x = [i for i in range(list_size)]
node_y = [i for i in range(list_size, 2 * list_size)]
node_z = [i for i in range(2 * list_size, num_nodes)]


def build_pauli_correlation_encoding(pauli, node_list, n, k=2):
    """Build Pauli correlation encoding for the given pauli and node list."""
    pauli_correlation_encoding = []
    for idx, c in enumerate(combinations(range(n), k)):
        if idx >= len(node_list):
            break
        paulis = ["I"] * n
        paulis[c[0]], paulis[c[1]] = pauli, pauli
        pauli_correlation_encoding.append(("".join(paulis)[::-1], 1))

    hamiltonian = []
    for pauli, weight in pauli_correlation_encoding:
        hamiltonian.append(SparsePauliOp.from_list([(pauli, weight)]))

    return hamiltonian


pauli_correlation_encoding_x = build_pauli_correlation_encoding(
    "X", node_x, num_qubits
)
pauli_correlation_encoding_y = build_pauli_correlation_encoding(
    "Y", node_y, num_qubits
)
pauli_correlation_encoding_z = build_pauli_correlation_encoding(
    "Z", node_z, num_qubits
)

problem_setup_time = time.time() - start_problem
print(f"✓ Problem setup completed in {problem_setup_time:.4f}s\n")

# ============================================================================
# Step 2: Build and optimize quantum circuit
# ============================================================================
print("Building and optimizing quantum circuit...")
start_circuit = time.time()

qc = efficient_su2(num_qubits, ["ry", "rz"], reps=2)
print(f"Circuit: {num_qubits} qubits, {qc.num_parameters} parameters, depth {qc.depth()}")

pm = generate_preset_pass_manager(backend=aer, optimization_level=3)
qc_optimized = pm.run(qc)
print(f"Optimized circuit depth: {qc_optimized.depth()}")

circuit_time = time.time() - start_circuit
print(f"✓ Circuit optimization completed in {circuit_time:.4f}s\n")

# ============================================================================
# Step 3: Define loss function
# ============================================================================
print("Setting up loss function and optimizer...")

experiment_results = []
iteration_times = []


def loss_func_estimator(x, ansatz, hamiltonian, estimator):
    """
    Calculate loss function using Pauli correlation encoding.
    """
    iter_start = time.time()

    job = estimator.run(
        [
            (ansatz, hamiltonian[0], x),
            (ansatz, hamiltonian[1], x),
            (ansatz, hamiltonian[2], x),
        ]
    )
    result = job.result()

    # Build expectation value map
    node_exp_map = {}
    idx = 0
    for r in result:
        for ev in r.data.evs:
            node_exp_map[idx] = ev
            idx += 1

    # Calculate loss with tanh smoothing
    loss = 0
    alpha = num_qubits
    for edge0, edge1 in graph.edge_list():
        if edge0 < len(node_exp_map) and edge1 < len(node_exp_map):
            loss += np.tanh(alpha * node_exp_map[edge0]) * np.tanh(
                alpha * node_exp_map[edge1]
            )

    # Regularization term
    regulation_term = 0
    for i in range(len(node_exp_map)):
        regulation_term += np.tanh(alpha * node_exp_map[i]) ** 2
    regulation_term = regulation_term / len(node_exp_map)
    regulation_term = regulation_term**2
    beta = 1 / 2
    v = len(graph.edges()) / 2 + (len(graph.nodes()) - 1) / 4
    regulation_term = beta * v * regulation_term

    loss = loss + regulation_term

    iter_time = time.time() - iter_start
    iteration_times.append(iter_time)

    print(f"  Iteration {len(experiment_results):3d} | Loss: {loss:10.6f} | Time: {iter_time:.4f}s")
    experiment_results.append({"loss": loss, "exp_map": node_exp_map})
    return loss


# ============================================================================
# Step 4: Run optimization
# ============================================================================
print("Starting optimization on AER simulator...")
start_optimization = time.time()

# Apply circuit layout to observables
pce = [
    [op.apply_layout(qc_optimized.layout) for op in pauli_correlation_encoding_x],
    [op.apply_layout(qc_optimized.layout) for op in pauli_correlation_encoding_y],
    [op.apply_layout(qc_optimized.layout) for op in pauli_correlation_encoding_z],
]

estimator = Estimator(mode=aer)

def loss_func(x):
    return loss_func_estimator(x, qc_optimized, [pce[0], pce[1], pce[2]], estimator)

np.random.seed(42)
initial_params = np.random.rand(qc_optimized.num_parameters)

# Run optimization with fewer iterations for demo
result = minimize(
    loss_func, initial_params, method="COBYLA", options={"maxiter": 10}
)

optimization_time = time.time() - start_optimization
print(f"\n✓ Optimization completed in {optimization_time:.4f}s\n")

# ============================================================================
# Step 5: Post-process results
# ============================================================================
print("Processing results...")

par0, par1 = set(), set()
for i in experiment_results[-1]["exp_map"]:
    if experiment_results[-1]["exp_map"][i] >= 0:
        par0.add(i)
    else:
        par1.add(i)

cut_size = calc_cut_size(graph, par0, par1)
print(f"Final cut size: {cut_size}")
print(f"Optimization result:\n{result}\n")

# ============================================================================
# Benchmarking Summary
# ============================================================================
print("=" * 70)
print("BENCHMARKING SUMMARY")
print("=" * 70)
print(f"Setup time (simulator creation):       {setup_time:10.4f}s")
print(f"Problem setup time:                    {problem_setup_time:10.4f}s")
print(f"Circuit setup & optimization time:     {circuit_time:10.4f}s")
print(f"Optimization loop time:                {optimization_time:10.4f}s")
print(f"  - Average time per iteration:        {np.mean(iteration_times):10.4f}s")
print(f"  - Min iteration time:                {np.min(iteration_times):10.4f}s")
print(f"  - Max iteration time:                {np.max(iteration_times):10.4f}s")
print(f"Total runtime:                         {setup_time + problem_setup_time + circuit_time + optimization_time:10.4f}s")
print("=" * 70)

plt.show()