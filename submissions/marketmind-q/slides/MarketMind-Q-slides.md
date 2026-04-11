# MarketMind-Q Observatory

## 1. MarketMind-Q

A compiler-aware benchmark for finance QML.

We benchmark quantum kernels against strong classical ML, then use qBraid to test whether the quantum workload survives compilation across representations and execution environments.

## 2. Finance Is A Hostile Benchmark

Financial labels are short-horizon, low-signal, and regime-dependent.

A useful quantum claim needs strong baselines, no future leakage, and date-respecting evaluation.

## 3. One Dataset, One Target, One Timeline

Sector ETF rows from 2018-01-01 through 2026-03-31.

SPY is the market benchmark. The target is whether a sector ETF beats SPY by more than 0.25% over the next five trading days.

## 4. Classical Baselines Are Strong

The classical panel is intentionally credible:

- Logistic regression
- RBF SVM
- Random forest
- XGBoost

Every model uses the same frozen rows, walk-forward splits, target, and metrics.

## 5. Quantum Kernel SVM

The QML model maps past-only finance features into a Qiskit `zz_feature_map`, estimates compute-uncompute kernel probabilities, and trains an SVM with a precomputed kernel.

Modes:

- Exact statevector
- 1024-shot finite sampling
- Noisy 1024-shot proxy

## 6. Boundary Result

QML is not a universal winner.

The central result is a boundary map: where the quantum kernel is useful, where it is merely competitive, and where classical ML dominates.

Best positive slice: train size 160, feature dimension 2, cutoff 2023-01-03, QML ROC-AUC edge near +0.152.

## 7. qBraid Compiler-Aware Layer

The same quantum-kernel workload is compiled through qBraid:

- Qiskit source to QASM2 roundtrip back to Qiskit
- Qiskit source to Cirq

The benchmark compares source and compiled zero-state probabilities, Hellinger distance, depth, two-qubit gates, serialized size, runtime, and shots.

## 8. qBraid Result

qBraid produced 64 successful rows across two strategies and four execution environments.

QASM2 roundtrip preserves kernel probability exactly under statevector execution. Cirq statevector is effectively exact near numerical precision, with a different resource profile.

## 9. Web Demo

MarketMind-Q Observatory turns the CSV evidence into a judge-ready story:

- Boundary Map
- Model Arena
- qBraid Lab
- Judge Tour

The first screen connects CML vs QML to qBraid compiler portability.

## 10. Final Claim

MarketMind-Q is a boundary map, not a hype claim.

CML still wins often. QML can be competitive in specific slices. qBraid makes portability measurable by comparing output quality against compiled-resource cost.

Research and education only. Not investment advice.
