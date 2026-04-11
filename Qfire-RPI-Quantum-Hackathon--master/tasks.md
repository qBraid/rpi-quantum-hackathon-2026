# QuantumProj Tasks

## Current Project State

This repository is no longer a mock-only shell. It has a working FastAPI backend, a wired React frontend, persisted SQLite storage, seeded wildfire scenarios, and an end-to-end product flow with real simulator-backed quantum benchmarking.

## Done and Complete

### Backend

- FastAPI app scaffold is complete.
- SQLite persistence is implemented with SQLAlchemy models for:
  - `Scenario`
  - `RiskRun`
  - `ForecastRun`
  - `OptimizationRun`
  - `BenchmarkRun`
  - `Report`
  - `IntegrationStatus`
- Scenario CRUD endpoints are implemented:
  - `POST /api/scenarios`
  - `GET /api/scenarios`
  - `GET /api/scenarios/{id}`
  - `PATCH /api/scenarios/{id}`
  - `DELETE /api/scenarios/{id}`
- Risk modeling endpoints are implemented:
  - `POST /api/risk/run`
  - `GET /api/risk/runs/{id}`
- Forecast endpoints are implemented:
  - `POST /api/forecast/run`
  - `GET /api/forecast/runs/{id}`
- Optimization endpoints are implemented:
  - `POST /api/optimize/run`
  - `GET /api/optimize/runs/{id}`
- Benchmark endpoints are implemented:
  - `POST /api/benchmarks/run`
  - `GET /api/benchmarks`
  - `GET /api/benchmarks/{id}`
- Report endpoints are implemented:
  - `POST /api/reports/generate`
  - `GET /api/reports`
  - `GET /api/reports/{id}`
- Integration and overview endpoints are implemented:
  - `GET /api/integrations/status`
  - `GET /api/overview`
  - `GET /api/health`
- Seeded wildfire scenarios are created on startup.
- Basic backend tests exist and pass.

### Product Logic

- Wildfire-first 10x10 editable grid workflow exists.
- Classical, quantum-style, and hybrid risk comparison exists.
- Time-step wildfire propagation forecast exists.
- Intervention optimization exists with:
  - full-grid classical baseline
  - reduced critical-subgraph quantum study
  - hybrid recommendation
- Benchmarking is tied to the intervention problem, not a disconnected demo.
- Benchmark degraded mode is honest when qBraid / Qiskit / simulator dependencies are unavailable.
- IBM availability is surfaced as simulator-only when credentials are missing.
- Backend structure is organized into `routes`, `schemas`, and `services`.
- Reports are generated from stored scenario and run artifacts.

### Frontend

- Marketing homepage exists.
- Login/auth shell page exists.
- App shell navigation exists.
- Overview page is wired to backend overview and recent records.
- Scenario library is wired to backend scenarios.
- Scenario workspace can load, edit, save, and create scenarios.
- Risk page can run live backend risk analysis.
- Forecast page can run live backend forecast analysis.
- Optimize page can run live backend optimization.
- Benchmarks page can run and inspect benchmark records.
- Benchmark detail page exists.
- Reports page can generate and preview stored reports.
- Integrations page is wired to backend integration status.
- Settings page shows runtime/workspace state.
- Frontend build passes.

## Partially Done

### Quantum / Benchmarking

- qBraid is structurally central to the benchmark workflow.
- Compiler-aware benchmarking UX exists.
- Availability detection exists.
- Degraded behavior is honest.
- Real qBraid-backed simulator execution is active through a qBraid conversion bridge and Qiskit compilation flow.
- IBM-backed execution is not yet validated end to end.

### Authentication

- Login screen exists.
- Real authentication, session management, user accounts, and authorization are not implemented.

### Reports

- Reports are generated and exportable as markdown.
- PDF export, shareable links, and presentation mode are not implemented.

## Still Needs To Be Done

### Highest Priority MVP Gaps

- Add real IBM execution support when credentials are available and validate it end to end.
- Add a backend route or frontend caching strategy for recent run lookup by scenario to make reports and workflow pages smoother.

### Important Product Gaps

- Add true run history views for risk, forecast, and optimization, not just benchmark/report history.
- Add better comparison UX across multiple runs.
- Add richer charts and visual summaries instead of JSON-heavy detail surfaces in some places.
- Add scenario validation and friendlier error messaging around malformed grids and settings.
- Add delete/archive confirmation UX and toast notifications.
- Add true auth and workspace ownership if the MVP needs multiple users.

### Engineering / Quality Gaps

- Add more backend unit tests around service logic, not just route flow tests.
- Add frontend tests.
- Replace deprecated `datetime.utcnow()` usage with timezone-aware UTC timestamps.
- Add linting and formatting standards if they are going to be enforced in CI.
- Add API error typing and more robust frontend retry / failure handling.
- Consider code-splitting the frontend bundle; the current build warns about large chunks.

## Recommended Definition Of MVP Complete

The MVP should be considered complete when the following are true:

- Scenario -> Risk -> Forecast -> Optimize -> Benchmark -> Report works reliably from the UI.
- qBraid-backed benchmark runs execute for real in at least simulator mode.
- IBM execution is optional but correctly enabled when credentials are present.
- Degraded mode remains explicit and honest.
- `.env.example`, READMEs, and launch instructions match actual runtime behavior.
- Core flows have test coverage and can be launched locally without guesswork.
