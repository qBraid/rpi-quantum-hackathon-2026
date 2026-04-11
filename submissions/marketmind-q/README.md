# MarketMind-Q qBraid Submission

MarketMind-Q is a compiler-aware quantum machine learning benchmark for short-horizon finance classification. It compares strong classical ML baselines against a Qiskit quantum-kernel SVM, then uses qBraid to test whether the quantum-kernel estimation workload preserves useful output probabilities after compilation across program representations and execution environments.

## Links

- Code repository: https://github.com/Taz33m/mktmind-qtm
- Submission commit: https://github.com/Taz33m/mktmind-qtm/commit/5a6c7531cb211a2fe3356fd108f945cd2fd30735
- Live dashboard: https://taz33m.github.io/mktmind-qtm/
- Presentation: https://1drv.ms/p/c/03e11cee1c77546a/IQDw_VDqkbWrQ5pN5H4g-CxQAVg0A8jGMhH_s51hpA6pb20

## Challenge Answers

| Required question | Answer |
|---|---|
| What algorithm did you implement? | A quantum-kernel SVM for short-horizon finance classification. It classifies whether a sector ETF beats SPY over the next five trading days by more than 0.25%. |
| What was your source representation? | Qiskit `QuantumCircuit` objects for compute-uncompute quantum-kernel estimation circuits built from Qiskit `zz_feature_map`. |
| How did qBraid transform the workload? | qBraid transpiled the Qiskit kernel circuit to QASM2 and back to Qiskit, and separately transpiled the Qiskit circuit to Cirq. The workflow also records available qBraid conversion paths with `ConversionGraph()`. |
| What two compilation strategies did you compare? | `qasm2_roundtrip`: Qiskit -> qBraid QASM2 -> qBraid Qiskit. `cirq_direct`: Qiskit -> qBraid Cirq. |
| What execution environments did you use? | `qiskit_statevector`, `qiskit_shots_1024`, `cirq_statevector`, and `cirq_shots_1024`. |
| What changed in the compiled programs? | Program type, circuit depth, two-qubit gate count, serialized size, measurement count, transpile time, and execution time. |
| Which strategy best preserved algorithm performance? | `qasm2_roundtrip / qiskit_statevector` preserved kernel probabilities exactly in this benchmark, with mean absolute probability error `0.0000`. |
| What was the cost of that strategy in compiled resources? | Mean compiled depth `21`, mean two-qubit gate count `9`, mean serialized size `634`, and exact statevector execution with no shots. |

## Metrics Reported

Output-quality metrics:

- Source zero-state probability
- Compiled zero-state probability
- Absolute probability error
- Mean and max absolute probability error
- Hellinger distance between Bernoulli distributions
- Optional qBraid circuit allclose result when available

Compiled-resource metrics:

- Program type
- Circuit depth
- Qubit count
- Two-qubit gate count
- Measurement count
- Serialized size
- Transpile seconds
- Execution seconds
- Shot count
- Status and error message

## Reproduction

The repository README contains full setup and reproduction instructions. The main commands are:

```bash
python -m src.build_dataset --start 2018-01-01 --end 2026-03-31
python -m src.run_benchmark --config configs/sector_etf.yaml
python -m src.qbraid_benchmark --config configs/qbraid.yaml
python -m src.make_report --config configs/sector_etf.yaml
```

The static judge dashboard is reproducible with:

```bash
cd web
npm install
npm run build
```

## Conclusion

Quantum kernels are not claimed to beat classical ML everywhere. The project instead maps where QML is useful, competitive, or impractical under low-data financial regimes, then uses qBraid to make the portability and compiled-resource cost of the quantum workload measurable.
