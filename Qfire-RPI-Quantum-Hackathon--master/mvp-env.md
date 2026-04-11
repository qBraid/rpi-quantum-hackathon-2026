# QuantumProj MVP Environment Requirements

## Purpose

This file defines the `.env` values that are actually needed for the current MVP and which ones are optional.

## Current Backend Code Expectations

The backend currently reads these environment variables:

- `QUANTUMPROJ_DB_PATH`
- `QBRAID_API_KEY`
- `QISKIT_IBM_TOKEN`
- `QISKIT_IBM_CHANNEL`
- `QISKIT_IBM_INSTANCE`

The current `Backend/.env.example` now matches the code.

## Minimum `.env` Needed For MVP

### Backend

Strictly required for local MVP launch:

- none

Because:

- SQLite defaults automatically
- simulator-only mode works without credentials
- the app does not hard-fail when quantum credentials are missing

### Recommended Backend `.env`

```env
# Optional SQLite override
QUANTUMPROJ_DB_PATH=Backend/quantumproj.db

# Optional qBraid access
QBRAID_API_KEY=

# Optional IBM Quantum access
QISKIT_IBM_TOKEN=
QISKIT_IBM_CHANNEL=ibm_quantum_platform
QISKIT_IBM_INSTANCE=
```

## What Each Variable Does

### `QUANTUMPROJ_DB_PATH`

- Optional
- Overrides where the SQLite database file is stored
- If omitted, the backend uses the default local DB path

### `QBRAID_API_KEY`

- Optional for current MVP launch
- Enables authenticated qBraid access
- Local simulator-backed benchmark execution can still run when the SDK stack is installed

### `QISKIT_IBM_TOKEN`

- Optional for current MVP launch
- Needed to make IBM hardware execution available
- Without it, the platform remains simulator-only

### `QISKIT_IBM_CHANNEL`

- Optional metadata/config for IBM connection

### `QISKIT_IBM_INSTANCE`

- Optional metadata/config for IBM connection

## Frontend `.env`

Optional:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

If omitted, the frontend already defaults to this URL in code.

## MVP Environment Modes

### Mode 1: Local Simulator-Only MVP

Needed:

- Python dependencies
- Node dependencies
- no quantum credentials required

Result:

- full app launches
- seeded scenarios work
- risk / forecast / optimize / reports work
- benchmarks run in simulator-backed mode if the SDK stack is installed, otherwise degrade honestly

### Mode 2: qBraid-Ready Simulator MVP

Needed:

- everything from local simulator-only mode
- installed `qbraid`
- installed `qiskit`
- `QBRAID_API_KEY`

Result:

- benchmark engine can execute real qBraid-centered compile-and-simulate runs

### Mode 3: IBM-Enabled MVP

Needed:

- everything from qBraid-ready mode
- `QISKIT_IBM_TOKEN`
- optional `QISKIT_IBM_CHANNEL`
- optional `QISKIT_IBM_INSTANCE`

Result:

- integrations page can honestly report hardware availability
- benchmark execution can optionally target IBM environments

## Recommended Next Action

Validate IBM-ready mode with a correct `QISKIT_IBM_TOKEN`, `QISKIT_IBM_CHANNEL`, and `QISKIT_IBM_INSTANCE` combination if hardware-backed execution is required next.
