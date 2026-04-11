# qBraid Challenge: Compiler-Aware Quantum Benchmarking

This project benchmarks how well a nontrivial quantum algorithm survives qBraid compilation under realistic execution constraints.

## What this implements

- **Algorithm:** QAOA for weighted MaxCut on a 4-node graph (with a chord edge).
- **Language:** Python
- **Source framework representation:** Qiskit `QuantumCircuit`
- **qBraid usage:** `qbraid.transpile(...)`, `ConversionGraph`, `ConversionScheme`
- **Two compilation strategies compared:**
  - Strategy A: constrained conversion search to **OpenQASM2** (`max_path_depth=2`, low attempts)
  - Strategy B: flexible conversion search to **OpenQASM3** (`max_path_depth=None`, higher attempts)
- **Two execution environments:**
  - Ideal simulator (`qiskit_aer.AerSimulator`)
  - Noisy + constrained simulator (custom noise model + linear coupling map + restricted basis gates)

## Repository structure

- `benchmark_qbraid_qaoa.py`: Main runnable benchmark script
- `requirements.txt`: Python dependencies
- `results/benchmark_results.json`: Output file generated after running

## Getting started

1. Create and activate a Python 3.10+ environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run benchmark:

```bash
python benchmark_qbraid_qaoa.py --shots 2048 --grid-points 6
```

4. Inspect generated output:

```bash
type results\\benchmark_results.json
```

## Metrics collected

### Output-quality metrics

- Success probability (probability of sampling optimal-cut bitstrings)
- Approximation ratio

### Compiled-resource metrics

- Circuit depth
- 2-qubit gate count (`cx` + `cz` + `ecr`)
- Circuit width

## Required challenge questions

### 1) What algorithm did you implement?

QAOA (p=1) for weighted MaxCut, with coarse parameter tuning over $(\gamma, \beta)$.

### 2) What was your source representation?

Qiskit `QuantumCircuit` built directly in Python.

### 3) How did qBraid transform the workload?

The tuned source circuit is transformed by qBraid into alternative target IRs/frameworks and then converted back to Qiskit for apples-to-apples execution benchmarking.

### 4) What two compilation strategies did you compare?

- Strategy A: constrained search (`ConversionScheme(max_path_attempts=2, max_path_depth=2)`) with target `qasm2`
- Strategy B: flexible search (`ConversionScheme(max_path_attempts=6, max_path_depth=None)`) with target `qasm3`

### 5) What changed in the compiled programs?

Resource characteristics changed after compilation (depth and two-qubit gate count), which impacts performance under the noisy constrained environment.

### 6) Which strategy best preserved algorithm performance?

Run-dependent. The script computes this directly from measured quality metrics and reports `best_tradeoff_strategy` in JSON output.

### 7) What was the cost of that strategy in compiled resources?

Reported side-by-side in `strategy_results` using depth, width, and 2-qubit gate count.

## Conclusion method

The script chooses a quality/cost winner using:

$$
\text{tradeoff score} = \frac{\text{noisy approximation ratio}}{\max(\text{2-qubit gate count}, 1)}
$$

This makes the winning strategy explicit while still reporting raw quality and raw cost metrics.
