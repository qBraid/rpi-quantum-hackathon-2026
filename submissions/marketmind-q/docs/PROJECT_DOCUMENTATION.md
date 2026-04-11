# MarketMind-Q Project Documentation

This document explains what was built, why the project took this shape, and what was tried during implementation. It is written as an implementation and decision log rather than a private chain-of-thought transcript.

## 1. Project Goal

MarketMind-Q was built to compete in the Classical ML vs Quantum ML challenge while also satisfying the qBraid compiler-aware benchmarking challenge.

The project answers two linked questions:

1. Can a quantum-kernel classifier be useful or competitive for short-horizon, market-relative finance classification under low-data constraints?
2. If that QML workload is useful, does the quantum-kernel estimation subroutine survive qBraid compilation across program representations and execution environments?

The final project is intentionally a benchmark, not a trading application. That choice keeps the work scientifically defensible and avoids overclaiming market prediction ability.

## 2. What Was Built

The project contains five main layers:

- Dataset builder: pulls sector ETF and SPY data, engineers past-only features, creates the five-day SPY-relative target, and freezes the resulting CSV.
- Classical/QML benchmark: evaluates classical baselines and a manual Qiskit quantum-kernel SVM on identical walk-forward splits.
- qBraid compiler benchmark: reconstructs a representative QSVM split, builds compute-uncompute kernel circuits, compiles them through qBraid, and measures output preservation versus compiled resource cost.
- Report generator: writes summary CSVs, markdown summaries, and figures.
- Web dashboard: turns the generated CSV/PNG artifacts into a judge-friendly exploratory demo.

## 3. Why Finance QML

The finance framing was chosen because it is difficult in exactly the ways that make a QML comparison interesting:

- Labels are noisy.
- Useful signals are small.
- Regimes change over time.
- Low-data slices matter.
- Classical baselines can be very strong.

That makes a simple “quantum wins” claim unlikely and untrustworthy. The stronger claim is a boundary map: where QML helps, where it is competitive, and where classical ML dominates.

## 4. Dataset And Target Decisions

The benchmark uses sector ETFs:

```text
XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY
```

SPY is used only as the market benchmark.

The target is:

```text
target = 1 if ((close[t+5] / close[t] - 1) - (SPY[t+5] / SPY[t] - 1)) > 0.0025 else 0
```

The target was chosen because absolute return prediction is often dominated by broad market direction. SPY-relative outperformance asks a cleaner classification question: did the sector beat the market by a small but nonzero margin?

Feature engineering was restricted to past-only values: lagged returns, volatility, volume ratios, relative strength, SPY volatility, and calendar seasonality. This was a deliberate guard against leakage.

## 5. Evaluation Design

The benchmark uses walk-forward cutoffs instead of random splits. This matters because financial rows are time-dependent, and random splits can leak regime information.

The main comparison grid uses:

- quarterly cutoffs from `2023-01-03` through `2025-10-01`
- train sizes `40`, `80`, `160`, `320`
- quantum feature dimensions `2` and `4`
- identical metrics for all models

Training rows are class-balanced from recent eligible history before each cutoff. This makes low-data comparisons less dominated by class imbalance.

## 6. Classical Baseline Rationale

The classical baseline panel is intentionally strong:

- Logistic regression checks whether a simple linear decision boundary is enough.
- RBF SVM is the closest classical analogue to a nonlinear kernel classifier.
- Random forest gives a robust tree-based baseline.
- XGBoost gives a strong boosted-tree baseline.

This prevents the QML result from looking good only because the classical comparison was weak.

## 7. QML Implementation Rationale

The QML model is a quantum-kernel SVM using Qiskit `zz_feature_map`.

The implementation uses a manual precomputed-kernel path:

1. Select top `d` features on the training split only.
2. Scale selected features to `[0, pi]`.
3. Build Qiskit feature-map statevectors or compute-uncompute circuits.
4. Estimate kernel probabilities.
5. Train `sklearn.svm.SVC(kernel="precomputed")`.

The manual precomputed-kernel path was chosen to keep the project robust if high-level Qiskit Machine Learning APIs change. It also makes the kernel matrix and circuit resource metrics explicit.

## 8. Quantum Execution Modes

The benchmark reports:

- `statevector_exact`: exact kernel probabilities from Qiskit statevectors.
- `shots_1024`: finite-shot sampling from exact probabilities.
- `noisy_1024`: finite-shot sampling with a conservative noise proxy.

The fallback sampling path exists because the local macOS sandbox could import `qiskit-aer` but failed when `AerSimulator.run()` tried to open OpenMP shared memory. The code still supports Aer on normal machines through:

```bash
export MARKETMIND_Q_USE_AER=1
```

## 9. qBraid Benchmark Rationale

The qBraid challenge asks whether a quantum algorithm survives compilation across frameworks and execution targets.

The chosen workload is not a standalone toy circuit. It is the quantum-kernel estimation subroutine used by the QSVM classifier. The algorithmic objective is to preserve the kernel-entry probability `p(|00...0>)`, because those probabilities define the QSVM kernel matrix.

The qBraid benchmark:

1. Loads the best existing `quantum_kernel_svm / statevector_exact` row by ROC-AUC.
2. Reconstructs the same train/test split and quantum preprocessing.
3. Builds a deterministic batch of 16 compute-uncompute circuits.
4. Computes the source Qiskit zero-state probability.
5. Compiles the circuits through qBraid.
6. Executes the compiled programs in exact and shot-limited environments.
7. Records output-quality and compiled-resource metrics.

## 10. qBraid Strategies And Environments

Two qBraid strategies are compared:

- `qasm2_roundtrip`: Qiskit -> qBraid `transpile(..., "qasm2")` -> qBraid `transpile(..., "qiskit")`
- `cirq_direct`: Qiskit -> qBraid `transpile(..., "cirq")`

Four execution environments are recorded:

- `qiskit_statevector`
- `qiskit_shots_1024`
- `cirq_statevector`
- `cirq_shots_1024`

`ConversionGraph()` is used to record the available qBraid paths in `results/qbraid_path_summary.csv`.

## 11. qBraid Metrics

Output-quality metrics:

- source zero-state probability
- compiled zero-state probability
- absolute probability error
- Bernoulli Hellinger distance
- optional `qbraid.interface.circuits_allclose`

Compiled-resource metrics:

- program type
- qubits
- depth
- two-qubit gates
- measurement count
- serialized size
- transpile seconds
- execution seconds
- shots
- status and error message

The benchmark records failed conversions as rows and continues other strategies. It exits nonzero only if every qBraid strategy fails.

## 12. qBraid Result

The qBraid run produced 64 successful rows.

Summary:

- `qasm2_roundtrip / qiskit_statevector`: mean absolute probability error `0.0000`, mean depth `21`, mean two-qubit gates `9`.
- `qasm2_roundtrip / qiskit_shots_1024`: mean absolute probability error about `0.0109`, same compiled resources, 1024 shots.
- `cirq_direct / cirq_statevector`: mean absolute probability error about `7.03e-8`, mean depth `37`, mean two-qubit gates `8`.
- `cirq_direct / cirq_shots_1024`: mean absolute probability error about `0.0084`, 1024 shots.

Conclusion: QASM2 roundtrip is the best quality/depth tradeoff for this workload, while Cirq direct also preserves exact output quality to numerical precision with a different compiled-resource profile. Shot-limited environments show the expected sampling floor.

## 13. Web Dashboard Rationale

The web dashboard was added because judges should not have to inspect CSVs to understand the result.

The dashboard is static and artifact-driven:

- It reads generated CSVs and PNGs.
- It does not run quantum jobs in the browser.
- It does not call live market APIs.
- It starts directly on the usable dashboard, not a landing page.

The first-screen story visual connects:

```text
finance signal -> CML champion vs QML kernel -> qBraid portability check
```

Dashboard sections:

- Boundary Map: shows QML edge versus the best classical model.
- Model Arena: compares models on the selected split.
- qBraid Lab: shows compiler strategy quality versus compiled-resource cost.
- Judge Tour: provides a short presentation path.

## 14. Presentation Rationale

The presentation story is built around one sentence:

> MarketMind-Q shows that quantum kernels do not beat classical ML everywhere, but they can become competitive in specific low-data financial regimes, and qBraid makes the practical cost of using them measurable by testing whether the quantum workload survives compilation across representations and execution environments.

The slides avoid claiming financial prediction power. They focus on benchmark rigor, boundary analysis, and compiler-aware quantum workload evaluation.

## 15. What Was Tried

Several implementation paths were tested or considered:

- MarketMind app integration was considered, then rejected. A standalone hackathon repository was cleaner, easier to reproduce, and safer for judging.
- Finance QML was selected over a generic toy dataset because it creates a stronger Classical ML vs QML comparison.
- A high-level Qiskit Machine Learning QSVC path was avoided for the core implementation because API shifts could create fragility. The manual precomputed-kernel path is more transparent.
- Aer execution was attempted but was unreliable in the local sandbox because of OpenMP shared-memory errors. A deterministic finite-shot fallback was added, while keeping Aer support available behind `MARKETMIND_Q_USE_AER=1`.
- A qBraid-only export step was rejected as too shallow. The final qBraid layer measures both output preservation and compiled resources.
- Braket was kept out of the v1 qBraid implementation to avoid dependency bloat and keep the submission reproducible.
- A web app was added after the benchmark worked, because the dashboard makes the story easier to judge quickly.
- AI-generated slide imagery was considered, but structured diagrams were better produced as editable PowerPoint/web-native shapes so text stays reliable.

## 16. Known Limits

- The benchmark is not a trading system.
- The qBraid layer measures preservation of kernel-entry probabilities, not a full retraining of the QSVM after every compiled execution path.
- Real hardware execution is future work.
- Shot-limited Qiskit execution uses deterministic sampling unless Aer is explicitly enabled.
- The dataset is frozen for reproducibility, so live market changes are intentionally out of scope.

## 17. Reproducibility Checklist

Core commands:

```bash
python -m src.build_dataset --start 2018-01-01 --end 2026-03-31
python -m src.run_benchmark --config configs/sector_etf.yaml
python -m src.qbraid_benchmark --config configs/qbraid.yaml
python -m src.make_report --config configs/sector_etf.yaml
python -m pytest
```

Web dashboard:

```bash
cd web
npm install
npm run sync-data
npm run dev
```

Deck generation:

```bash
cd slides/observatory-deck
npm install
npm run build
```

## 18. Final Positioning

MarketMind-Q should be presented as a disciplined benchmark instrument:

- It gives classical ML a fair fight.
- It gives QML a realistic low-data setting.
- It gives qBraid a central role in testing quantum workload portability.
- It reports both quality and cost.

That combination is the main reason the project is competitive for both the Classical ML vs QML and qBraid challenge tracks.
