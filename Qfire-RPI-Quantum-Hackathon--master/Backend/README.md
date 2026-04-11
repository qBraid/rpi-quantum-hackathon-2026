# QuantumProj Backend

FastAPI backend for the QuantumProj MVP. This service owns persisted scenarios, risk runs, propagation forecasts, intervention optimization runs, compiler-aware benchmark records, reports, and integration capability state.

## What it does

- Stores wildfire-first 10x10 spatial scenarios in SQLite
- Runs a real classical-vs-QML wildfire early-ignition-corridor classification study on the same scenario-derived dataset
- Simulates stochastic ensemble propagation forecasts with time steps, burn duration, dryness, wind, slope, and spotting
- Produces intervention plans with:
  - full-grid classical planning on the 10x10 adjacency graph
  - strict K=10 intervention handling
  - reduced critical-subgraph quantum study
  - recommended deployable plan with before/after connectivity and expected-burn metrics
- Exposes qBraid-centered benchmark records and labels degraded mode honestly when qBraid and Qiskit are missing
- Generates markdown-friendly decision reports from persisted run artifacts

## Architecture

The backend is now organized under `Backend/app/` with package folders for routes, schemas, and services.

- `main.py`
  - FastAPI app creation, CORS, route registration, startup bootstrap
- `db.py`
  - SQLAlchemy engine, session factory, dependency injection helper
- `models.py`
  - ORM models for `Scenario`, `RiskRun`, `ForecastRun`, `OptimizationRun`, `BenchmarkRun`, `Report`, and `IntegrationStatus`
- `schemas/*.py`
  - Pydantic request/response contracts per module
- `services/scenarios.py`
  - Scenario CRUD and version bumps
- `services/risk.py`
  - ensemble-derived wildfire dataset generation plus classical logistic regression and Qiskit variational quantum classification
- `services/forecast.py`
  - stochastic ensemble wildfire spread simulation plus shift-kernel diagnostics
- `services/optimize.py`
  - Full-grid forecast-aware intervention planning plus reduced quantum study
- `services/wildfire_model.py`
  - shared wildfire semantics, fuel parameters, environment controls, probabilistic ignition logic, and ensemble summary helpers
- `algorithms/qaoa.py`
  - QAOA problem formulation, real Qiskit circuit construction, and simulator execution helpers
- `algorithms/shift.py`
  - low-depth shift diagnostics used by the forecast module
- `services/benchmarks.py`
  - qBraid-centered benchmark orchestration, compilation strategy comparison, and execution metric collection
- `services/reports.py`
  - Report assembly and markdown export payload generation
- `services/integrations.py`
  - qBraid / Qiskit / IBM / simulator capability detection
- `services/bootstrap.py`
  - Seeded wildfire scenarios for first launch
- `routes/*.py`
  - FastAPI route modules mapped to product areas

## Honesty rules implemented here

- No fake hardware availability
- No fake qBraid benchmark results
- If `qbraid` or `qiskit` is missing, benchmark runs are stored as degraded and explicitly say why
- If IBM credentials are missing, the platform remains usable in simulator-only mode
- Optimization labels full-scale classical versus reduced quantum study scope separately

## Wildfire science note

Risk, forecast, and optimization now share one planning-grade wildfire model.

Normalized states:

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

Each state maps to centralized parameters including:

- base ignitability
- burn duration
- fuel load
- spotting propensity
- treatment resistance
- spread receptivity

Shared environmental controls:

- dryness
- wind speed
- wind direction
- slope influence
- spotting likelihood
- suppression effectiveness

This backend is designed for preseason or scenario-analysis planning. It is not an operational fire behavior or incident command system.

## Wildfire optimization note

The optimization engine is now explicitly challenge-aligned:

- `planning` mode:
  - keeps the deployable plan on the full 10x10 grid
  - uses the shared wildfire forecast model in the objective loop
  - combines adjacency disruption with expected burned-area reduction and corridor pressure
  - only marks a plan as `recommended` if it does not worsen burned-area outcomes beyond the safety tolerance
- `challenge` mode:
  - keeps the same 10x10 grid and strict `K=10`
  - builds the challenge graph from adjacency among `dry_brush` and `ignition` cells
  - exposes the challenge cost explicitly:
    - `C = sum_(i,j in E)(1 - x_i)(1 - x_j) + (sum_i x_i - 10)^2`
  - uses the reduced QAOA study as a tractable subgraph carved from that same challenge graph

This is split honestly across execution scales:

- Full-scale planning stays classical so the entire hillside can be optimized.
- The quantum study first shortlists the highest-impact cells and then runs on a smaller critical candidate subset derived from the same objective family.
- The final result never pretends a full 100-qubit NISQ solve is currently practical.
- Planning mode and challenge mode are stored and labeled separately so the compliance story is explicit.

## Forecast realism note

The forecast service no longer relies on a simple deterministic threshold.

It now models:

- probabilistic ignition
- multi-step burning before burnout
- directional wind effects
- slope-assisted spread
- ember spotting
- run-to-run environmental variation

Stored forecast outputs include:

- representative sample snapshots
- burn probability map
- expected ignition time map
- corridor summaries
- final burned area distribution
- planning-grade summary statistics

## Risk modeling note

The risk engine now answers the Classical ML vs Quantum ML challenge more directly:

- Binary task:
  - predict whether a cell belongs to the early ignition corridor within the planning response window
- Dataset:
  - generated from repeated ensemble spread simulations over reproducible scenario variants derived from the selected hillside
- Shared feature set:
  - `fuel_load`
  - `base_ignitability`
  - `local_fuel_density`
  - `distance_risk`
  - `wind_exposure`
  - `slope_factor`
  - `treated`
  - `connectivity_proxy`
- Models compared:
  - classical logistic regression via scikit-learn
  - shallow Qiskit variational quantum classifier
  - optional hybrid probability ensemble
- Metrics collected:
  - accuracy
  - precision
  - recall
  - F1
  - AUROC
  - runtime

This stays honest: the QML model is a real comparator on the same binary task, but it is not forced to beat the classical baseline.

## API surface

Core product endpoints:

- `POST /api/scenarios`
- `GET /api/scenarios`
- `GET /api/scenarios/{id}`
- `PATCH /api/scenarios/{id}`
- `DELETE /api/scenarios/{id}`
- `POST /api/risk/run`
- `GET /api/risk/runs/{id}`
- `POST /api/forecast/run`
- `GET /api/forecast/runs/{id}`
- `POST /api/optimize/run`
- `GET /api/optimize/runs/{id}`
- `POST /api/benchmarks/run`
- `GET /api/benchmarks`
- `GET /api/benchmarks/{id}`
- `POST /api/reports/generate`
- `GET /api/reports`
- `GET /api/reports/{id}`
- `GET /api/integrations/status`
- `GET /api/overview`
- `GET /api/health`

## Environment variables

Backend variable names are standardized to:

- `QUANTUMPROJ_DB_PATH`
- `QBRAID_API_KEY`
- `QISKIT_IBM_TOKEN`
- `QISKIT_IBM_INSTANCE`
- `CORS_ORIGINS`

Use [`.env.example`](.env.example) as the canonical backend template.

## Runtime modes

### Simulator-only

- no IBM credentials, invalid IBM credentials, or no hardware connectivity
- ideal and noisy simulator execution remains available
- benchmark runs still execute when the local SDK stack is installed

### qBraid-ready

- `qbraid`, `qiskit`, `qiskit-aer`, and `qiskit-qasm3-import` installed
- benchmark engine builds a real Qiskit QAOA workload
- qBraid is used as the conversion and normalization layer in the compile workflow
- two qBraid-centered compilation strategies are compared with real compiled metrics

### IBM-ready

- `QISKIT_IBM_TOKEN` plus a valid instance / CRN when needed
- IBM readiness is surfaced honestly in integrations
- benchmark runs can include real IBM Runtime execution when credentials are valid

## Launch guide

From `Backend/`:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If you need to install dependencies first:

```powershell
python -m pip install -r requirements.txt
```

Health check:

```powershell
curl http://127.0.0.1:8000/api/health
```

## Tests

From the repository root:

```powershell
pytest Backend/test_api.py
```

Current verification status:

- `pytest Backend/test_api.py Backend/test_services.py` passes
- local imports verified for:
  - `qbraid`
  - `qiskit`
  - `qiskit-aer`
  - `qiskit-ibm-runtime`
  - `qiskit-qasm3-import`

## Direct benchmark script

For a UI-free benchmark run:

```powershell
cd Backend
python scripts/run_benchmark.py
```

Add `ibm_hardware` to the environment list when IBM Runtime is configured and available.

## Benchmark implementation note

The benchmark engine now answers the qBraid challenge requirements directly:

- Algorithm:
  - reduced-subgraph wildfire intervention QAOA
- Source representation:
  - `qiskit.QuantumCircuit`
- qBraid usage:
  - `ConversionGraph` to expose conversion paths
  - `qbraid.transpile(..., "qasm2")`
  - `qbraid.transpile(..., "qasm3")`
  - qBraid round-trip normalization back into Qiskit before target preparation
- Strategies compared:
  - `Portable OpenQASM 2 bridge`
    - generic line-topology CX preparation
  - `Target-aware OpenQASM 3 bridge`
    - heavy-hex-like constrained preparation with ECR-style basis
- Execution environments:
  - ideal simulator
  - noisy simulator
  - IBM Runtime hardware when credentials are valid
- Metrics collected:
  - approximation ratio
  - success probability
  - expected cost
  - depth
  - two-qubit gate count
  - width
  - total gate count
  - shots
  - gate breakdown

The benchmark summary now produces a direct conclusion string that compares quality preservation against compiled cost instead of reporting raw transpilation numbers only.

## Planning-grade disclaimer

The wildfire modules are deliberately simplified and comparative. They are intended to help users:

- compare scenario variants
- identify likely spread corridors
- estimate relative intervention impact
- evaluate benchmark integrity for reduced quantum workloads

They should not be used as a replacement for operational fire behavior models, field intelligence, or emergency command systems.

## Future extension points

- Replace SQLite with PostgreSQL by swapping the SQLAlchemy database URL
- Add async job execution if runs become long-lived
- Add authenticated user/workspace ownership to the scenario and report models
