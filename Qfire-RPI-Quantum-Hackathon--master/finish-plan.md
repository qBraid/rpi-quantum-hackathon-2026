# QuantumProj Finish Plan

## Goal

Finish the project as a believable MVP where the full workflow is stable, qBraid benchmarking is real, environment handling is clean, and the product can be shown without caveats beyond normal MVP limitations.

## Estimated Remaining Work

If worked in focused order:

### Fast path

- 2 to 4 focused implementation sessions to reach a strong MVP

### More realistic polished path

- 1 to 2 weeks of iterative cleanup, validation, and UX refinement

This depends mostly on how much real qBraid + IBM execution you want to complete before calling it done.

## Step-By-Step Plan

## Completed Recently

- `Backend/.env.example` has been corrected and standardized
- backend env variable names are aligned with the code
- simulator-only, qBraid-ready, and IBM-ready runtime modes are now documented clearly
- `qbraid`, `qiskit`, `qiskit-aer`, and `qiskit-ibm-runtime` are installed and importable locally
- benchmark availability now detects real SDK readiness
- the backend app has been reorganized into:
  - `app/routes`
  - `app/schemas`
  - `app/services`
- the benchmark engine now uses:
  - a real Qiskit-built QAOA circuit
  - qBraid conversion bridging
  - two compilation strategies
  - real ideal and noisy simulator execution
  - stored compiled resource metrics
- risk, forecast, optimization, benchmark, and report routes now support scenario-scoped retrieval where needed
- the frontend core workflow pages were simplified to remove filler UI and focus on the runnable workflow
- reports now support explicit run selection instead of relying only on latest-run fallback
- scenario authoring now includes templates, save feedback, and archive/delete confirmations
- backend service tests and frontend smoke tests are in place

## Phase 1: Fix environment and benchmark realism

### Step 1

Normalize environment configuration.

Do:

- update `Backend/.env.example`
- use the same variable names everywhere
- document simulator-only vs qBraid-ready vs IBM-ready clearly

Status:

- completed

### Step 2

Install and verify `qbraid` and `qiskit` in the backend environment.

Do:

- add packages to backend requirements or a documented optional install path
- confirm imports work locally
- confirm integration status reflects actual availability

Status:

- completed

### Step 3

Implement real qBraid-centered benchmark execution.

Do:

- build the reduced intervention workload using actual Qiskit objects
- pass it through qBraid-centered compilation/transpile flow
- compare at least two compilation strategies
- record real compiled resource metrics

Status:

- completed for simulator-backed benchmarking

Remaining extension:

- optionally add IBM-backed benchmark execution when runtime access is valid

## Phase 2: Complete the end-to-end workflow polish

### Step 4

Improve run history and retrieval by scenario.

Do:

- add list endpoints or filtered queries for risk, forecast, and optimization runs
- surface recent runs in the frontend for each module
- make reports choose from explicit prior runs, not only latest fallback

Output:

- stronger operational feel
- easier repeat usage

Status:

- completed

### Step 5

Upgrade benchmark and report UX.

Do:

- replace JSON-heavy readouts with structured tables and metric cards
- add clearer quality-vs-cost visualization labeling
- add export affordances beyond markdown if desired

Output:

- product looks less developer-facing and more enterprise-ready

Status:

- completed for the current MVP
- markdown and JSON export are both available from the report workspace

### Step 6

Tighten scenario workspace UX.

Do:

- add better editing affordances
- add save success/error feedback
- add archive/delete confirmations
- add scenario templates and cleaner constraint editing

Output:

- scenario authoring becomes reliable enough for demos and internal use

Status:

- completed

## Phase 3: Reliability and production readiness

### Step 7

Expand backend tests.

Do:

- add service-level tests for risk, forecast, optimize, and benchmark logic
- test degraded benchmark mode explicitly
- test integration status behavior with and without env vars

Output:

- core logic is safer to modify

Status:

- completed

### Step 8

Add frontend tests and smoke coverage.

Do:

- add basic page rendering and API integration tests
- cover main workflow navigation

Output:

- fewer regressions during polish

Status:

- completed with lightweight smoke coverage for shell navigation and explicit report generation inputs

### Step 9

Clean up technical debt.

Do:

- replace deprecated UTC timestamp usage
- consider frontend bundle splitting
- standardize lint/format/test commands

Output:

- healthier baseline for future work

Status:

- partially completed

Completed:

- UTC timestamp usage is already standardized on `datetime.now(timezone.utc)`
- frontend test scripts were added: `npm run test` and `npm run test:run`
- Vite build config now includes basic chunk splitting for router and chart code

Remaining:

- chart bundle size is still over the warning threshold, so route-level lazy loading or deeper chart isolation is still worth doing
- lint/format command standardization is still incomplete because the repo does not yet have ESLint/Prettier wired in

## Phase 4: Optional but high-value MVP extensions

### Step 10

Add real auth if needed.

Do:

- choose a simple auth provider
- add session-aware route protection
- associate scenarios and reports with users/workspaces

Output:

- usable by more than one person safely

### Step 11

Add richer exports.

Do:

- PDF generation
- shareable report links
- presentation-mode report view

Output:

- better stakeholder-facing output

## Recommended Finish Order
 
If the goal is to ship the best MVP quickly, do this order:

1. Verify IBM-ready mode with a valid token, channel, and instance
2. Add route-level lazy loading for benchmark-heavy frontend pages
3. Add ESLint/Prettier and standardize `backend` / `frontend` check commands
4. Optionally add IBM-backed benchmark execution paths once runtime access is valid
5. Add richer exports if stakeholder-facing delivery matters

## Short Assessment

The project is now a coherent working MVP rather than a scaffold. The qBraid benchmark layer is real in simulator-backed execution, the core workflow pages are operational and simpler, and the main remaining work is IBM validation plus the last production-hardening tasks around bundle size and tooling consistency.
