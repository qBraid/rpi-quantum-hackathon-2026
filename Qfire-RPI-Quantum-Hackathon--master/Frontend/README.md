# QuantumProj Frontend

Vite + React + TypeScript frontend for the QuantumProj MVP. The repository already contained a routed React shell, so the implementation extends that structure in place instead of replacing it with Next.js.

## What it does

- Presents the full product workflow:
  - Scenario Setup
  - Risk Modeling
  - Propagation Forecast
  - Intervention Optimization
  - Compiler-Aware Benchmarking
  - Report Generation
- Wires all major operational pages to the FastAPI backend
- Shows simulator-only and degraded benchmark states explicitly
- Uses seeded wildfire scenarios so the platform is usable immediately after launch

## Architecture

The frontend lives under `Frontend/src/app/`.

- `api.ts`
  - Typed fetch client for the FastAPI backend
- `types.ts`
  - Shared frontend API types
- `useAsyncData.ts`
  - Minimal async data loading helper
- `components/AppShell.tsx`
  - Main product shell, global navigation, status banner
- `components/product.tsx`
  - Shared product UI primitives like headers, panels, status pills, grids, empty/loading states
- `scenarioUtils.ts`
  - Grid helpers and cell-state options
- `pages/*.tsx`
  - Product pages:
    - `HomePage`
    - `LoginPage`
    - `DashboardPage`
    - `ScenariosPage`
    - `ScenarioWorkspacePage`
    - `RiskPage`
    - `ForecastPage`
    - `OptimizePage`
    - `BenchmarksPage`
    - `BenchmarkDetailPage`
    - `ReportsPage`
    - `IntegrationsPage`
    - `SettingsPage`
- `routes.tsx`
  - React Router configuration

## Product behavior notes

- Scenario pages use real persisted backend records
- Risk, forecast, optimize, benchmark, and report pages call live APIs
- Benchmark pages never pretend hardware or qBraid availability
- When the backend reports simulator-only mode, the shell surfaces that globally
- The benchmark page still works in degraded mode, but it clearly explains why compiled benchmark results are unavailable

## Environment variables

Optional:

- `VITE_API_BASE_URL`
  - Defaults to `http://127.0.0.1:8000/api`

Example:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api"
```

## Launch guide

Install dependencies:

```powershell
cd Frontend
npm.cmd install
```

Run the dev server:

```powershell
npm.cmd run dev
```

Default expectation:

- Frontend dev server on Vite default port
- Backend running separately on `http://127.0.0.1:8000`

## Production build

From `Frontend/`:

```powershell
npm.cmd run build
```

Current verification status:

- `npm.cmd run build` passes

## Backend dependency

The app expects the FastAPI backend in `Backend/` to be running. Launch that first:

```powershell
cd Backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then launch the frontend:

```powershell
cd Frontend
npm.cmd run dev
```

## Known MVP constraints

- Auth is a launch-ready shell, not a real identity system yet
- Compiler-aware benchmarking is only fully active when the backend has real qBraid + Qiskit capability
- The frontend keeps the existing Vite architecture from the repo rather than migrating the project to Next.js mid-build
