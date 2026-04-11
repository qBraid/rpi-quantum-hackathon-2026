# QuantumProj Overview Summary

## What QuantumProj Is

QuantumProj is a spatial decision intelligence platform for constrained systems. It is designed to help teams model spatial risk, simulate how that risk propagates, plan limited interventions, and evaluate whether classical, quantum, or hybrid solvers are actually trustworthy under real execution constraints.

The current domain wedge is wildfire resilience.

## Core Product Workflow

The product is built around one connected workflow:

1. Scenario Setup
2. Risk Modeling
3. Propagation Forecast
4. Intervention Optimization
5. Compiler-Aware Benchmarking
6. Report Generation

This is intended to feel like one decision platform, not a collection of unrelated challenge pages.

## Product Thesis

QuantumProj does not claim quantum advantage by default.

Its value is:

- making constrained spatial planning usable in a clean product workflow
- comparing solver approaches honestly
- using qBraid-centered compiler-aware benchmarking to judge whether quantum results remain meaningful after compilation and realistic execution constraints

## Current Technical Shape

### Frontend

- React
- TypeScript
- Vite
- Tailwind-based styling

### Backend

- FastAPI
- Python
- SQLAlchemy
- SQLite

### Quantum Direction

- qBraid is central to benchmark execution integrity
- Qiskit is the primary source framework for the current benchmark workload
- IBM execution is optional when credentials are available
- simulator-only mode is supported by design

## Current MVP Scope

The current MVP is centered on:

- wildfire-first 10x10 grid scenarios
- side-by-side classical / quantum / hybrid analysis
- honest reduced-scope quantum optimization studies
- stored benchmark records
- generated decision reports

## What Is Already Strong

- The app has a real backend and real frontend wiring.
- The workflow exists end to end.
- The product language is coherent.
- Degraded mode is honest.
- The benchmark module is positioned as an execution-integrity layer, not decorative quantum branding.
- The benchmark engine now uses a real Qiskit QAOA workload with qBraid-centered conversion and simulator-backed execution.

## What Still Determines Final Quality

The main thing that will decide whether QuantumProj feels finished now is how well the real benchmark layer is polished, validated against IBM-ready execution, and integrated into the broader operational workflow.

If that is completed well, the project becomes a credible MVP for enterprise-facing spatial decision intelligence with quantum benchmarking as a meaningful trust layer.
