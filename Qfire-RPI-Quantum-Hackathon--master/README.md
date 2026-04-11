# QFire

QFire is a wildfire resilience planning and benchmarking application built around one operational workflow:

`Scenario -> Risk Map -> Spread Forecast -> Intervention Plan -> Benchmark Integrity -> Report`

The current product wedge is concrete: a planner or resilience analyst defines a 10x10 wildfire hillside, classifies early ignition corridor risk, simulates stochastic ensemble spread, places a strict budget of fire-resistant interventions, and then checks whether the reduced quantum optimization workload still behaves well after qBraid-centered compilation and execution.

## Which Challenges This Targets

QFire is structured to answer three hackathon tracks with one coherent product:

- `Quantum Partitioning for Wildfire Resilience`
  - full-grid wildfire intervention planning on a 10x10 adjacency graph with strict `K=10`
- `Classical ML vs Quantum ML`
  - real binary classification for early ignition prediction using the same dataset and evaluation framework for both models
- `qBraid Optimization Challenge`
  - compiler-aware benchmark study of a reduced wildfire intervention QAOA workload across qBraid-centered compilation strategies and multiple execution environments

It also includes low-depth shift diagnostics in the forecast module inspired by the fluid-dynamics challenge, but the submission focus is wildfire planning plus benchmark integrity.

## Product Use Case

The intended user is a wildfire planner, land management team, resilience analyst, or research/operations group evaluating mitigation strategies on a small hillside scenario.

The product is not a generic quantum dashboard. Each module supports the same wildfire decision chain:

1. Build or edit a hillside scenario.
2. Run early ignition corridor classification.
3. Forecast how spread may propagate under uncertainty.
4. Recommend where limited interventions should be placed to reduce likely burned area and corridor exposure.
5. Benchmark whether the reduced quantum optimization workflow survives realistic compilation and execution constraints.
6. Generate a report from explicit persisted runs.

## Technical Contributions

### Planning-Grade Wildfire Science Backbone

Risk, forecast, and optimization now use one shared wildfire semantics layer instead of separate heuristics.

Supported normalized cell semantics:

- `empty`
- `water`
- `road_or_firebreak`
- `dry_brush`
- `grass`
- `shrub`
- `tree`
- `protected`
- `intervention`
- `ignition`
- `burned`

Each state maps to centralized planning-grade parameters such as fuel load, ignitability, burn duration, spotting propensity, and treatment resistance. Shared environmental controls are also consistent across modules:

- dryness / fuel-moisture proxy
- wind speed
- wind direction
- slope influence
- spotting likelihood
- suppression / treatment effectiveness

This is not a live incident command fire physics solver. It is a comparative planning tool that uses simplified but internally consistent wildfire behavior to support preseason scenario analysis.

### Wildfire Forecasting Model

The forecast layer is now ensemble-based and stochastic rather than a single deterministic threshold rollout.

- discrete time-step simulation
- cells can remain burning for multiple steps before becoming burned
- ignition is probabilistic, not threshold-only
- wind acts directionally
- slope can accelerate uphill spread
- ember spotting can create occasional nonlocal ignitions
- treated and protected cells reduce risk rather than acting as perfect blockers

Forecast outputs now include:

- burn probability map
- expected ignition time map
- representative ensemble snapshots
- likely spread corridors
- final burned area distribution
- mean and percentile burned-area summaries

### Wildfire Optimization Mapping

The optimization engine maps directly onto the wildfire challenge framing:

- grid size: `10x10`
- spread pathways: orthogonal adjacency on flammable cells, interpreted through the same fuel semantics used in forecast and risk
- intervention budget: strict `K=10`
- objective: reduce surviving flammable links, ignition-connected corridors, expected burned area, and high-probability spread pathways

This is handled honestly at two scales:

- `planning` mode:
  - full-scale deployable planning is classical on the complete 10x10 grid
  - objective mixes adjacency disruption with forecast-aware burned-area outcomes
  - recommendation safety gates prevent a worse-burned-area plan from being shown as the default recommendation
- `challenge` mode:
  - uses the posted challenge-facing adjacency formulation on the 10x10 grid
  - strict `K=10`
  - challenge cost:
    - `C = sum_(i,j in E)(1 - x_i)(1 - x_j) + (sum_i x_i - 10)^2`
  - graph edges come from dry-brush fire-path adjacency
  - the reduced QAOA study is carved from the same challenge graph for tractable benchmarking

The UI and summaries explicitly distinguish `planning mode` from `challenge mode`, and in both cases they distinguish the `full classical layer` from the `reduced quantum study`.

### How This Satisfies The Wildfire Resilience Challenge

QuantumProj now answers the wildfire challenge in a direct, defendable way:

- the challenge-facing optimizer works on a `10x10` grid
- it enforces `K = 10` placements
- it builds a fire-path graph from adjacency among challenge flammable cells
- it exposes the challenge cost function explicitly
- it keeps a reduced QAOA study derived from the same graph
- it does not pretend a full 100-qubit hardware solve is currently practical

This means the repo can show:

- an exact challenge-facing formulation for judges
- a richer planning mode for product usefulness
- one honest bridge between the full wildfire graph and the reduced benchmarked quantum subproblem

### Classical ML vs Quantum ML Risk Modeling

The risk layer is a real binary classification workflow, not heuristic scoring.

- task:
  - predict whether a cell belongs to the early ignition corridor within the planning response window
- dataset:
  - reproducible ensemble spread simulations on scenario variants derived from the selected hillside
- shared features:
  - `fuel_load`
  - `base_ignitability`
  - `local_fuel_density`
  - `distance_risk`
  - `wind_exposure`
  - `slope_factor`
  - `treated`
  - `connectivity_proxy`
- models:
  - classical logistic regression
  - shallow Qiskit variational quantum classifier
  - optional probability-ensemble hybrid
- metrics:
  - accuracy
  - precision
  - recall
  - F1
  - AUROC
  - runtime

Current honest finding:

- the classical baseline is usually the best practical model
- the QML model is slower and trained on a reduced balanced subset
- the comparison is still meaningful because it is run on the same task and evaluation split

### What the Science Is and Is Not Claiming

QuantumProj is intended for planning-grade comparative analysis:

- compare scenarios
- identify likely exposure corridors
- test intervention placement choices
- stress-test reduced quantum workloads under compilation and execution constraints

It is not claiming:

- real-time incident prediction
- full fire physics fidelity
- exact operational behavior under field conditions
- full-scale 100-qubit deployable optimization on current NISQ hardware

### qBraid Benchmarking Workload

The benchmark module is the technical centerpiece of the repo.

- algorithmic workload:
  - reduced-subgraph wildfire intervention QAOA
- source representation:
  - `qiskit.QuantumCircuit`
- qBraid usage:
  - `ConversionGraph`
  - `qbraid.transpile(workload, "qasm2")`
  - `qbraid.transpile(workload, "qasm3")`
  - qBraid round-trip normalization back into Qiskit before target preparation
- compilation strategies compared:
  - `Portable OpenQASM 2 bridge`
  - `Target-aware OpenQASM 3 bridge`
- execution environments:
  - ideal simulator
  - noisy simulator
  - IBM Runtime hardware when credentials are valid
- metrics collected:
  - approximation ratio
  - success probability
  - expected cost
  - depth
  - two-qubit gate count
  - width
  - total gate count
  - shots

Benchmark question:

`Which qBraid-centered compilation strategy best preserves useful optimization behavior once the wildfire workload is compiled for realistic targets, and what compiled resource cost is paid for that behavior?`

## Final Tradeoff Summary

The current repo is intentionally honest:

- classical ML is usually the most practical risk model
- full 10x10 wildfire planning is solved classically because that is what is operationally credible today
- the reduced quantum study is where QAOA and qBraid-centered benchmarking are used to test whether the mitigation workload survives compilation and constrained execution
- the benchmark module exists to build trust in quantum-backed recommendations, not to claim quantum advantage

## Architecture

### Frontend

- `Frontend/`
  - Vite + React + TypeScript + Tailwind
  - wildfire-first workflow pages
  - live API wiring for scenarios, risk, forecast, optimize, benchmarks, and reports

Important files:

- [AppShell.tsx](Frontend/src/app/components/AppShell.tsx)
- [RiskPage.tsx](Frontend/src/app/pages/RiskPage.tsx)
- [OptimizePage.tsx](Frontend/src/app/pages/OptimizePage.tsx)
- [BenchmarksPage.tsx](Frontend/src/app/pages/BenchmarksPage.tsx)
- [BenchmarkDetailPage.tsx](Frontend/src/app/pages/BenchmarkDetailPage.tsx)

### Backend

- `Backend/`
  - FastAPI
  - SQLite via SQLAlchemy
  - modular route/schema/service structure
  - Qiskit, qBraid, Aer, IBM Runtime integration

Important files:

- [main.py](Backend/app/main.py)
- [risk.py](Backend/app/services/risk.py)
- [forecast.py](Backend/app/services/forecast.py)
- [optimize.py](Backend/app/services/optimize.py)
- [benchmarks.py](Backend/app/services/benchmarks.py)
- [qaoa.py](Backend/app/algorithms/qaoa.py)

### How the Modules Connect

- scenarios provide the shared 10x10 hillside state
- risk uses the scenario plus the shared wildfire model to generate a labeled wildfire classification dataset
- forecast simulates stochastic ensemble spread on the same grid
- optimize uses the same semantics and environment to score interventions under strict `K=10`
- benchmarks derive a reduced QAOA workload from the intervention problem
- reports assemble persisted run artifacts across the workflow

### Where qBraid and IBM Are Used

- qBraid is central in [benchmarks.py](Backend/app/services/benchmarks.py) as the compile/transpile backbone
- IBM Runtime is used in the benchmark hardware path through `SamplerV2` when credentials and backend availability allow it
- if IBM is unavailable, the benchmark degrades cleanly to simulator execution without fabricating hardware data

## Setup

### Prerequisites

- Python 3.11+ or compatible local environment
- Node 18+
- npm

### Backend Install

```powershell
cd Backend
python -m pip install -r requirements.txt
```

### Frontend Install

```powershell
cd Frontend
npm.cmd install
```

## Environment Variables

Backend variables are defined in [Backend/.env.example](Backend/.env.example):

- `QUANTUMPROJ_DB_PATH`
- `QBRAID_API_KEY`
- `QISKIT_IBM_TOKEN`
- `QISKIT_IBM_INSTANCE`
- `CORS_ORIGINS`

Frontend:

- `VITE_API_BASE_URL`

### Runtime Modes

`Simulator-only`

- no IBM credentials or no hardware connectivity
- ideal and noisy simulator benchmark execution still works if the SDK stack is installed

`qBraid-ready`

- `qbraid`, `qiskit`, `qiskit-aer`, and `qiskit-qasm3-import` installed
- benchmark workflow compares the two qBraid-centered strategies on simulators

`IBM-ready`

- valid `QISKIT_IBM_TOKEN`
- optional `QISKIT_IBM_INSTANCE`
- hardware path is available through IBM Runtime `SamplerV2`

## Run Instructions

### Start the Backend

```powershell
cd Backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Start the Frontend

```powershell
cd Frontend
npm.cmd run dev
```

Default API URL:

- `http://127.0.0.1:8000/api`

## Runnable Benchmark Entry Point

For judges who want the benchmark without using the UI:

```powershell
cd Backend
python scripts/run_benchmark.py
```

Optional hardware run:

```powershell
cd Backend
python scripts/run_benchmark.py --environments ideal_simulator noisy_simulator ibm_hardware
```

The script prints:

- scenario used
- run id and status
- benchmark availability mode
- best strategy
- best environment
- recommendation string
- per-strategy result records

## Tests

Backend:

```powershell
pytest Backend/test_api.py Backend/test_services.py -q
```

Frontend:

```powershell
cd Frontend
npm.cmd test -- --run
npm.cmd run build
```

Coverage focus:

- API flow and persistence
- shared wildfire state normalization and ensemble behavior
- risk dataset generation and ML/QML comparison
- forecast ensemble summaries and diagnostics
- wildfire optimization constraints, consistency, and explanations
- benchmark structure, metrics, and degraded mode behavior
- basic frontend navigation/report wiring smoke tests

## Repo Notes

- [Backend/README.md](Backend/README.md) contains backend-specific architecture and runtime notes
- [Frontend/README.md](Frontend/README.md) contains frontend-specific launch notes
- [SUBMISSION_SUMMARY.md](SUBMISSION_SUMMARY.md) contains a short judge-facing summary
