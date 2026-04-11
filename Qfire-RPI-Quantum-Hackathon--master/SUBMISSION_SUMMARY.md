# QuantumProj Submission Summary

## What Was Built

QuantumProj is a wildfire resilience planning application with an integrated quantum benchmarking layer. It supports one end-to-end workflow:

`Scenario -> Risk Map -> Spread Forecast -> Intervention Plan -> Benchmark Integrity -> Report`

The app is built as a real product workflow rather than disconnected challenge tabs.

## Challenges Addressed

- `Quantum Partitioning for Wildfire Resilience`
- `Classical ML vs Quantum ML`
- `qBraid Optimization Challenge`

## Algorithms and Frameworks Used

### Wildfire optimization

- full 10x10 adjacency-based intervention planning
- strict `K=10` intervention budget
- `planning` mode:
  - full-scale deployable planning handled classically
  - forecast-aware objective with recommendation safety gating
- `challenge` mode:
  - exact challenge-facing adjacency formulation
  - challenge cost:
    - `C = sum_(i,j in E)(1 - x_i)(1 - x_j) + (sum_i x_i - 10)^2`
  - dry-brush adjacency graph on the 10x10 grid
- reduced critical-subgraph study used for quantum optimization benchmarking and derived from the same graph family

### Risk modeling

- task:
  - classify whether a cell belongs to the early ignition corridor within the planning response window
- classical model:
  - scikit-learn logistic regression
- quantum model:
  - shallow Qiskit variational quantum classifier

### Benchmarking

- workload:
  - reduced-subgraph wildfire intervention QAOA
- source framework:
  - Qiskit
- qBraid usage:
  - `ConversionGraph`
  - `qbraid.transpile(..., "qasm2")`
  - `qbraid.transpile(..., "qasm3")`
  - qBraid round-trip normalization back into Qiskit

## What Was Benchmarked

Two qBraid-centered compilation strategies were compared:

- `Portable OpenQASM 2 bridge`
- `Target-aware OpenQASM 3 bridge`

Across execution environments:

- ideal simulator
- noisy simulator
- IBM Runtime hardware when available

Metrics collected:

- approximation ratio
- success probability
- expected cost
- depth
- two-qubit gate count
- width
- total gate count
- shots

## Key Finding

The repo does not claim quantum advantage.

Current honest findings:

- classical ML is generally the most practical wildfire risk classifier
- full 10x10 wildfire intervention planning is most credible when solved classically
- the reduced quantum study is meaningful as a compiler-aware benchmark workload
- qBraid is central because the benchmark is explicitly about how well the wildfire QAOA workload survives compilation across strategies and targets

## Why This Is Meaningful

This contribution is meaningful because it connects three challenge themes inside one coherent operational product:

- real wildfire planning context
- real classical-vs-QML comparison on the same task
- real qBraid-centered benchmark study on a nontrivial quantum workload tied to the product itself
- a direct wildfire challenge mode that judges can inspect independently from the richer planning mode

The result is reproducible, technically grounded, and easy to judge from either the UI or the benchmark script.
