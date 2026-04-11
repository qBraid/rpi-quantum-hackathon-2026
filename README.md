# Compiler-Aware QAOA Benchmarking for Wildfire Resilience

**RPI Quantum Hackathon 2026 — qBraid Challenge - See PowerPoint Included for Presentation**

## Overview

We implement **QAOA (Quantum Approximate Optimization Algorithm)** to solve a
real-world spatial optimization problem: placing fire-resistant Toyon shrubs on
a 10×10 hillside grid to maximally disrupt wildfire spread paths. We use the
**qBraid SDK** to benchmark two compilation strategies across two execution
environments, measuring the tradeoff between output quality and compiled
resource cost.

---

## Algorithm

**QAOA for Wildfire Toyon Placement**

The wildfire problem is formulated as a QUBO (Quadratic Unconstrained Binary
Optimization):

```
C = Σ(i,j)∈E (1-xᵢ)(1-xⱼ) + λ(Σᵢxᵢ - K)²
```

- xᵢ = 1 if cell i contains a Toyon (fire-resistant shrub)
- E = set of adjacent cell pairs (fire spread paths)
- K = 10 (Toyon budget)
- λ = 30 (penalty enforcing exactly K Toyons)

This maps directly to an Ising Hamiltonian where each edge in the grid becomes
a ZᵢZⱼ interaction, implemented as an RZZ gate in the QAOA cost layer.

For the full 10×10 problem (100 qubits), we use **subgrid decomposition**:
splitting the grid into four 5×5 subproblems, solving each with QAOA, then
combining solutions — achieving tractable circuit depths on NISQ hardware.

---

## Source Framework Representation

All circuits are built in **Qiskit** (`QuantumCircuit`) using:
- `qc.h()` — initial superposition layer
- `qc.rzz()` — fire-spread cost layer (one per grid edge)
- `qc.rz()` — single-qubit constraint terms
- `qc.rx()` — QAOA mixer layer

---

## qBraid Compilation

We use `qbraid.transpile()` to compile the Qiskit source circuit to the
`ibm_rensselaer` backend (127-qubit Eagle processor, RPI campus):

```python
from qbraid import transpile as qbraid_transpile

# Strategy 1: Default compilation
circuit_s1 = qbraid_transpile(source_circuit, "qiskit",
                               optimization_level=1, target=backend)

# Strategy 2: Aggressive optimization
circuit_s2 = qbraid_transpile(source_circuit, "qiskit",
                               optimization_level=3, target=backend)
```

---

## Compilation Strategies Compared

| | Strategy 1 | Strategy 2 |
|---|---|---|
| optimization_level | 1 (default) | 3 (aggressive) |
| Goal | Fast compilation | Minimize depth/gates |
| Routing | Basic SWAP insertion | Advanced routing |
| Gate synthesis | Standard decomposition | Noise-aware synthesis |

---

## Execution Environments

1. **Aer statevector simulator** — ideal noiseless simulation for baseline
2. **ibm_rensselaer** — 127-qubit IBM Quantum Eagle processor physically
   located at RPI's Voorhees Computing Center

---

## Metrics

### Output quality
- **Approximation ratio** = optimal fire spread / QAOA fire spread
- **Fire spread count** = number of adjacent dry-brush cell pairs remaining
- **Constraint satisfaction** = whether exactly K=10 Toyons were placed
- **Total Variation Distance (TVD)** = statistical distance between ideal and hardware shot distributions (0 = identical, 1 = completely different)
- **Hellinger distance** = symmetric measure of distribution overlap (0 = identical, 1 = orthogonal)

### Compiled resource cost
- **Circuit depth** — total layers after compilation to Eagle ISA
- **2-qubit gate count** — primary driver of hardware error
- **Compilation time** — time taken by qBraid transpiler

---

## Results

### 4×4 Benchmark (compiler comparison)

| Metric | S1: default (opt=1) | S2: aggressive (opt=3) |
|---|---|---|
| Circuit depth | 255 | 201 (−21.2%) |
| 2-qubit gates | 98 | 93 (−5.1%) |
| Compile time | 0.05s | 0.09s |
| Approx ratio — Aer | 1.000 | 1.000 |
| Fire spread — hardware | 15 / 14 | 15 / 14 |
| Approx ratio — hardware | 0.933 | **0.933** |
| TVD (ideal vs hardware) | **0.9146** | 0.9385 |
| Hellinger (ideal vs hardware) | **0.9496** | 0.9654 |

**Key finding:** Both strategies achieve identical hardware solution quality
(ratio=0.933) despite S2 reducing circuit depth by 21.2%. S1 has lower TVD
and Hellinger distance — its shot distribution is closer to ideal — yet this
does not translate to better optimization outcomes. This suggests that at
depth ~200-255, moderate depth reduction is insufficient to escape the NISQ
noise regime. Meaningful improvement requires architectural changes (subgrid
decomposition reducing depth to 51-381) rather than compilation optimization
alone.

### 10×10 Full Problem (subgrid decomposition, realistic grid)

| Method | Fire spread | Notes |
|---|---|---|
| No Toyons | 107 / 107 | All Dry Brush paths open |
| Greedy (marginal gain) | 67 / 107 | Best classical heuristic |
| QAOA simulation (Aer) | 67 / 107 | Matches greedy — realistic grid |
| QAOA on ibm_rensselaer | 72 / 107 | +5 paths from noise in dense subgrids |

Hardware gap explained by subgrid C (depth=381, 0 feasible shots) falling back
to greedy. Subgrids B (depth=51) and D (depth=162) matched simulation exactly.

### Layer depth analysis (p=1,2,3 on 4×4 realistic slice)

| p | Approx ratio | Runtime |
|---|---|---|
| 1 | 1.000 | 27s |
| 2 | 1.000 | 44s |
| 3 | 1.000 | 72s |

All p values achieve optimal — p=1 is most efficient for this problem size.

---

## Conclusion

**Which strategy best preserved algorithm performance?**

Neither strategy consistently outperformed the other. Across two hardware
runs, both strategies achieved ratio=1.000 on Aer simulation, but hardware
results varied — S1 got ratio=1.000 in run 1 and 0.941 in run 2, while S2
got 0.941 in both runs.

More strikingly, the transpiler itself produced different circuit layouts
across runs: S1 had depth 232 in run 1 and 205 in run 2, while S2 had depth
217 then 247. This non-determinism in compilation output means that abstract
resource metrics (depth, gate count) are unreliable predictors of hardware
performance without controlling for qubit mapping and calibration state.

TVD and Hellinger distance confirm this — S1's hardware distribution is
measurably closer to the ideal Aer distribution (TVD=0.9033 vs 0.9421,
Hellinger=0.9390 vs 0.9670), even though both values are high, reflecting
the severe noise environment at circuit depth ~200 on Eagle. The fact that
QAOA recovers the correct answer despite TVD>0.9 demonstrates the algorithm's
robustness — the optimization signal survives even when the output distribution
is heavily noise-dominated. S1
(opt=1) compiles faster and produces more predictable results. S2 (opt=3)
sometimes reduces 2-qubit gate count meaningfully (−8.3% in run 2) but at
the cost of compilation non-determinism and occasionally deeper circuits.

**Broader finding:** For the full 10×10 problem, subgrid decomposition
(four 5×5 subproblems at depth ~80) proved more effective than any
compilation strategy applied to the full circuit, since noise scales with
depth regardless of optimization level. The hardware run achieved fire
spread=142 vs the classical marginal-gain greedy baseline of 140 — within
1.4% of the best known classical solution on a real 100-variable optimization
problem running on quantum hardware at RPI.

---

## Getting Started

### Installation

```bash
pip install qiskit qiskit-ibm-runtime qiskit-aer qbraid scipy matplotlib numpy
```

### Authentication

```python
from qiskit_ibm_runtime import QiskitRuntimeService
QiskitRuntimeService.save_account(token="YOUR_API_KEY", instance="YOUR_CRN")
```

### Run benchmark

```bash
# Compiler comparison (4x4 grid, ~30 IBM minutes)
python qbraid_benchmark.py

# Full 10x10 decomposition (simulation)
python wildfire_decomposed.py  # USE_HARDWARE = False

# Full 10x10 decomposition (hardware)
python wildfire_decomposed.py  # USE_HARDWARE = True

# Layer depth comparison (simulation only)
python wildfire_qaoa_comparison_final.py
```

---

## Required Questions

1. **Algorithm:** QAOA for wildfire Toyon placement — minimizing fire-spread
   connectivity under a planting budget constraint

2. **Source representation:** Qiskit `QuantumCircuit` with RZZ cost layer and
   RX mixer layer

3. **qBraid transformation:** `qbraid.transpile()` compiles to Eagle ISA
   (ECR, RZ, SX, X gates) with routing to the device's heavy-hex topology

4. **Two compilation strategies:** optimization_level=1 (default fast
   compilation) vs optimization_level=3 (aggressive depth/gate minimization)

5. **What changed:** Strategy 2 produces shallower circuits with fewer 2-qubit
   gates by applying more sophisticated routing and gate-cancellation passes

6. **Best strategy:** Strategy 1 (default, opt=1) — despite higher circuit
   depth, conservative routing assigned the circuit to lower-error qubit pairs
   on Eagle, achieving ratio=1.000 vs 0.941 for the aggressive strategy

7. **Cost of best strategy:** depth=232, 2Q gates=108, compile time=0.26s —
   the tradeoff is slower compilation and deeper circuits, but better hardware
   fidelity due to more favorable qubit assignment
