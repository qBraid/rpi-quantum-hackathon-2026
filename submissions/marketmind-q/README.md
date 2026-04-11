# MarketMind-Q

MarketMind-Q is a reproducible finance benchmark for the RPI Quantum Hackathon. It compares strong classical ML baselines against a Qiskit quantum-kernel SVM, then uses qBraid to ask whether the quantum-kernel workload survives compilation across program representations and execution environments.

Core claim:

> Quantum kernels do not beat classical ML everywhere, but they can become competitive in specific low-data financial regimes, and qBraid makes the practical cost of using them measurable by testing whether the quantum workload preserves its kernel probabilities after compilation.

This is a research and education project, not a trading product.

## What We Built

- A frozen sector ETF dataset with date-respecting walk-forward splits.
- Classical baselines: logistic regression, RBF SVM, random forest, and XGBoost.
- A manual Qiskit quantum-kernel SVM using `zz_feature_map`.
- Exact, shot-limited, and noisy quantum execution modes.
- A qBraid compiler-aware benchmark for the QSVM kernel-estimation workload.
- A static React dashboard for the judge demo.
- Notebook, figures, results CSVs, and presentation materials.

Demo deck:

[MarketMind-Q Observatory presentation](https://1drv.ms/p/c/03e11cee1c77546a/IQDw_VDqkbWrQ5pN5H4g-CxQAVg0A8jGMhH_s51hpA6pb20)

Live dashboard:

[MarketMind-Q Observatory on GitHub Pages](https://taz33m.github.io/mktmind-qtm/)

qBraid submission note: the official hackathon submission should be opened as a PR to the challenge repository and include this repository plus the presentation link above.

## qBraid Challenge Answers

| Required question | Answer |
|---|---|
| What algorithm did you implement? | A quantum-kernel SVM for short-horizon finance classification. The algorithm classifies whether a sector ETF beats SPY over the next five trading days by more than 0.25%. |
| What was your source representation? | Qiskit `QuantumCircuit` objects for compute-uncompute quantum-kernel estimation circuits built from Qiskit `zz_feature_map`. |
| How did qBraid transform the workload? | qBraid transpiled the Qiskit kernel circuit to QASM2 and back to Qiskit, and separately transpiled the Qiskit circuit to Cirq. `ConversionGraph()` records the available conversion paths. |
| What two compilation strategies did you compare? | `qasm2_roundtrip`: Qiskit -> qBraid QASM2 -> qBraid Qiskit. `cirq_direct`: Qiskit -> qBraid Cirq. |
| What execution environments did you use? | `qiskit_statevector`, `qiskit_shots_1024`, `cirq_statevector`, and `cirq_shots_1024`. |
| What changed in the compiled programs? | Program type, depth, two-qubit gate count, serialized size, and measurement/runtime profile. QASM2 roundtrip produced Qiskit circuits; Cirq direct produced Cirq circuits and removed nonsemantic Qiskit barriers. |
| Which strategy best preserved algorithm performance? | `qasm2_roundtrip / qiskit_statevector` preserved kernel probabilities exactly in this benchmark, with mean absolute probability error `0.0000`. |
| What was the cost of that strategy? | Mean compiled depth `21`, mean two-qubit gate count `9`, mean serialized size `634`, exact statevector execution with no shots. |

The qBraid benchmark produced 64 successful rows across two compilation strategies and four execution environments.

## qBraid Metrics Summary

| Strategy | Execution environment | Rows | Mean abs. probability error | Max abs. probability error | Mean Hellinger distance | Mean depth | Mean 2Q gates | Shots |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `qasm2_roundtrip` | `qiskit_statevector` | 16 | `0.0000` | `0.0000` | `0.0000` | `21` | `9` | exact |
| `qasm2_roundtrip` | `qiskit_shots_1024` | 16 | `0.0109` | `0.0210` | `0.0109` | `21` | `9` | 1024 |
| `cirq_direct` | `cirq_statevector` | 16 | `7.03e-8` | `2.15e-7` | `8.84e-8` | `37` | `8` | exact |
| `cirq_direct` | `cirq_shots_1024` | 16 | `0.0084` | `0.0210` | `0.0090` | `37` | `8` | 1024 |

Interpretation: exact compilation paths preserve the kernel-estimation probabilities; shot-limited paths expose the expected sampling floor. QASM2 roundtrip is the best quality/depth tradeoff for this workload, while Cirq direct preserves output quality almost exactly under statevector simulation with a different resource profile.

## Classical ML vs QML Benchmark

Universe:

```text
XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY
```

Market benchmark:

```text
SPY
```

Target:

```text
target = 1 if ((close[t+5] / close[t] - 1) - (SPY[t+5] / SPY[t] - 1)) > 0.0025 else 0
```

Features are past-only: lagged returns, rolling volatility, volume ratios, relative strength versus SPY, SPY volatility, weekday seasonality, and month seasonality.

Evaluation design:

- Data period: `2018-01-01` through `2026-03-31`.
- Test cutoffs: quarterly from `2023-01-03` through `2025-10-01`.
- Train sizes: `40`, `80`, `160`, `320`.
- Quantum feature dimensions: `2` and `4`.
- No random train/test split.
- No future values in features.

## Setup

Use Python 3.10.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install optional qBraid dependencies:

```bash
pip install -r requirements-qbraid.txt
```

Install web dashboard dependencies:

```bash
cd web
npm install
cd ..
```

## Reproduce The Benchmark

Build or refresh the frozen dataset:

```bash
python -m src.build_dataset --start 2018-01-01 --end 2026-03-31
```

Run the full classical/QML benchmark:

```bash
python -m src.run_benchmark --config configs/sector_etf.yaml
```

Run the qBraid compiler-aware benchmark:

```bash
python -m src.qbraid_benchmark --config configs/qbraid.yaml
```

Generate figures and summary:

```bash
python -m src.make_report --config configs/sector_etf.yaml
```

Run tests:

```bash
python -m pytest
```

Fast smoke run:

```bash
python -m src.run_benchmark --config configs/smoke.yaml
python -m src.make_report --config configs/smoke.yaml
```

## Run The Web Dashboard

MarketMind-Q Observatory is a static React dashboard that reads the generated benchmark artifacts from `results/`. It does not call live finance APIs or run quantum jobs in the browser.

```bash
cd web
npm run sync-data
npm run dev
```

Open the local Vite URL shown in the terminal.

Dashboard sections:

- Boundary Map: QML ROC-AUC edge versus best classical model.
- Model Arena: same split, same metrics, all model families.
- qBraid Lab: compiler strategy quality versus compiled-resource cost.
- Judge Tour: 90-second presentation path.

## Important Outputs

- `data/marketmind_qml_dataset.csv`
- `results/metrics_summary.csv`
- `results/kernel_resources.csv`
- `results/qbraid_compile_metrics.csv`
- `results/qbraid_path_summary.csv`
- `results/results_summary.md`
- `results/figures/qml_edge_heatmap.png`
- `results/figures/score_cost_frontier.png`
- `results/figures/qbraid_quality_cost.png`
- `results/figures/qbraid_strategy_resources.png`
- `notebooks/MarketMind_QML_Finance_Benchmark.ipynb`
- `slides/MarketMind-Q-slides.md`
- `slides/MarketMind-Q-Observatory.pptx`
- `web/`

## Repository Map

```text
configs/                  Benchmark configs
data/                     Frozen dataset
docs/                     Design rationale and project notes
notebooks/                Reproducible narrative notebook
results/                  Metrics, summaries, and generated figures
slides/                   Presentation materials
src/                      Python benchmark implementation
tests/                    Unit and smoke tests
web/                      Static React dashboard
```

## Notes On Execution Modes

The main QML benchmark defaults to Qiskit statevector fidelities plus binomial shot sampling for shot-limited modes. This avoids a known sandbox failure where `qiskit-aer` can import but `AerSimulator.run()` crashes while opening OpenMP shared memory.

On a normal local machine, set this before running the benchmark to use Aer execution for shot-based kernels:

```bash
export MARKETMIND_Q_USE_AER=1
```

The qBraid benchmark uses exact Qiskit statevectors, deterministic shot sampling for the Qiskit shot environment, and Cirq simulation for Cirq exact/shot environments.

## Additional Documentation

For implementation rationale, tradeoffs, and an experiment log, see:

`docs/PROJECT_DOCUMENTATION.md`

## Research And Education Disclaimer

This project is for research, education, and hackathon demonstration only. It is not investment advice, does not recommend trades, and does not guarantee future market performance.
