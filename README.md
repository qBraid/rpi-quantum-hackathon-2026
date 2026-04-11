# Quantum Hackathon Wildfire Benchmark Suite

This project benchmarks wildfire mitigation optimization workflows using a dependency-injected architecture. The suite compares quantum circuit compilation strategies and runtime environments to identify optimal quality/cost tradeoffs.

## Project Structure

- `src/problems/wildfire/` – wildfire mitigation problem using the layer-optimized circuit layout
- `src/executors/qiskit_executor.py` – Qiskit runtime executor
- `src/executors/qbraid_executor.py` – qBraid-focused executor (including qBraid Quantum Cloud support)
- `src/optimizers/` – SPSA and SciPy-based optimization backends
- `src/main.py` – composition root with matrix orchestration and benchmark comparison logic

## Execution Environments

The benchmark supports four runtime modes:

- `hardware` – run on a real IBM Quantum backend
- `aer` – run on an Aer simulator seeded from an IBM backend configuration
- `clifford` – run locally on the Aer stabilizer simulator
- `cloud` – run on qBraid Quantum Cloud using a qBraid device ID

## Quickstart (uv)

### 1) Clone and enter the project

```bash
git clone <your-repo-url>
cd quantum_hackathon
```

### 2) Ensure `uv` is installed

```bash
uv --version
```

### 3) Create/sync the virtual environment from lockfile

```bash
uv sync
```

This creates `.venv` (if needed) and installs dependencies from `uv.lock`.

### 4) Verify CLI wiring

```bash
uv run python src/main.py --help
```

### 5) Configure IBM Runtime credentials

Create a `.env` file in the project root for `hardware` and `aer` flows:

```bash
cat > .env <<'EOF'
QISKIT_IBM_CHANNEL=ibm_cloud
QISKIT_IBM_TOKEN=your_token_here
QISKIT_IBM_URL=https://cloud.ibm.com
QISKIT_IBM_INSTANCE=your_crn_or_service_name
EOF
```

`clifford` mode does not require IBM credentials.

### 5b) Configure qBraid cloud credentials (optional)

Set `QBRAID_API_KEY` in your `.env` file for cloud mode:

```bash
cat >> .env <<'EOF'
QBRAID_API_KEY=your_qbraid_api_key
EOF
```

### 6) Verify CLI wiring

```bash
uv run python src/main.py --help
```

## Running Benchmarks

The wildfire benchmark compares quantum circuit compilation strategies and execution environments. Use `uv run` to invoke all commands.

### Single-run examples

Clifford simulator (no credentials required):

```bash
uv run python src/main.py --grid-rows 10 --grid-cols 10 --shrub-budget 10
```

Qiskit on a specific IBM backend:

```bash
uv run python src/main.py --executor qiskit --mode aer --backend ibm_rensselaer --grid-rows 10 --grid-cols 10
```

qBraid balanced strategy on hardware:

```bash
uv run python src/main.py --executor qbraid --qbraid-strategy balanced --qbraid-environment hardware --backend ibm_rensselaer --grid-rows 10 --grid-cols 10
```

qBraid cloud mode:

```bash
uv run python src/main.py --executor qbraid --qbraid-environment cloud --qbraid-strategy balanced --backend <qbraid_device_id> --grid-rows 10 --grid-cols 10 --qbraid-shots 2048
```

### Artistic 3D shrub placement plot (PyVista + Matplotlib)

Render an artistic 3D tile map and place shrubs as three rotating GLB tree models from `assets/kenney_nature-kit/Models/GLTF format`:

```bash
uv run python src/plot_wildfire_3d.py --grid-rows 10 --grid-cols 10 --shrub-budget 10
```

Optional: render off-screen and export a PNG snapshot:

```bash
uv run python src/plot_wildfire_3d.py --grid-rows 10 --grid-cols 10 --shrub-budget 10 --save-image outputs/wildfire_3d.png
```

### Benchmarking and comparison matrices

**Recommended: qBraid strategy comparison**

Compare compilation strategies across execution environments:

```bash
uv run python src/main.py \
  --run-matrix \
  --benchmark-executors qbraid \
  --benchmark-qbraid-strategies balanced aggressive \
  --benchmark-qbraid-environments hardware aer clifford cloud \
  --grid-rows 10 \
  --grid-cols 10 \
  --shrub-budget 10 \
  --layer-reps 2
```

**Executor comparison**

Compare qiskit and qbraid on shared environments:

```bash
uv run python src/main.py \
  --run-matrix \
  --benchmark-executors qiskit qbraid \
  --benchmark-qiskit-modes clifford aer \
  --benchmark-qbraid-strategies balanced aggressive \
  --benchmark-qbraid-environments clifford aer \
  --grid-rows 10 \
  --grid-cols 10 \
  --shrub-budget 10
```

### Benchmarking parameters

**Wildfire problem parameters:**

- `--grid-rows`: grid row count (default: 20)
- `--grid-cols`: grid column count (default: 20)
- `--shrub-budget`: Toyon shrub budget (default: 15)
- `--brush-probability`: chance a cell starts as dry brush (default: 0.3)
- `--wildfire-seed`: random seed for landscape generation
- `--layer-reps`: layer-optimized circuit repetitions (default: 1)

**Executor parameters:**

- `--executor`: executor implementation (`qiskit` or `qbraid`)
- `--mode` (Qiskit): execution backend (`hardware`, `aer`, `clifford`)
- `--backend`: IBM backend name or qBraid device ID
- `--qbraid-strategy`: compilation strategy (`balanced`, `aggressive`)
- `--qbraid-environment`: execution environment (`hardware`, `aer`, `clifford`, `cloud`)
- `--qbraid-shots`: shots per iteration in cloud mode (default: 1024)

**Matrix benchmarking parameters:**

- `--run-matrix`: enable matrix mode
- `--benchmark-executors`: executors to compare
- `--benchmark-qiskit-modes`: Qiskit modes to compare
- `--benchmark-qbraid-strategies`: qBraid strategies to compare
- `--benchmark-qbraid-environments`: qBraid environments to compare

## Benchmark Design

### Algorithm

This benchmark performs **wildfire mitigation** optimization leveraging QAOA. The default optimizer is a hardware-friendly **SPSA** backend, selected through dependency injection for robustness on real quantum hardware.

### Architecture

The benchmark is organized around a composition root in `src/main.py` that wires together:

- a **problem** object (`src/problems/wildfire/`)
- an **executor** object (`src/executors/...`)
- an **optimizer** object (`src/optimizers/...`)

## Compilation Strategies

The qBraid executor supports the following compilation strategies in matrix mode:

- `balanced` – balanced transpilation for quality and speed
- `aggressive` – aggressive optimization for minimal gate count

## Metrics Collected

The benchmark records the following metrics from each wildfire run:

- **Circuit metrics**
  - Circuit depth (`depth`)
  - Circuit size (`size`)
  - Two-qubit gate count (`two_qubit_ops`)
  - Transpilation time (`transpile_time`)

- **Optimization metrics**
  - Fire-break score (`fire_break_score`)
  - Optimization loss (`loss`)
  - Optimized parameters (gamma, beta)

- **Quality metrics**
  - Quality score (`quality_score`)
  - Compiled resource cost (`compiled_resource_cost`)
  - Tradeoff score (`tradeoff_score`)

For wildfire, logs also report the optimized `gamma` and `beta` parameters with fixed-precision formatting, and plots overlay selected Toyon sites on the risk map.

## Best Quality/Cost Tradeoff

The best tradeoff is the combination with the highest observed `tradeoff_score` in the matrix summary output. For reproducible reporting, record the best observed `tradeoff_score` from the latest matrix execution and cite its `run_label`, `optimizer_method`, and `fire_break_score`.

## Command-Line Options

### Global options

- `--executor`: selects the executor implementation (`qiskit` or `qbraid`) for single-run mode
- `--run-matrix`: run all selected executor/option combinations
- `--headless`: disable all wildfire visualization windows (Matplotlib 2D + PyVista 3D)

### Problem parameters

- `--grid-rows`: grid row count (default: 20)
- `--grid-cols`: grid column count (default: 20)
- `--shrub-budget`: Toyon shrub budget (default: 15)
- `--brush-probability`: chance that a cell starts as dry brush (default: 0.3)
- `--wildfire-seed`: random seed for landscape generation
- `--layer-reps`: layer-optimized circuit repetitions (default: 1)

### Qiskit executor options

- `--mode`: execution backend (`hardware`, `aer`, `clifford`)
- `--backend`: IBM backend name used for `hardware` and `aer` modes
- `--maxiter`: COBYLA iteration limit

### qBraid executor options

- `--qbraid-strategy`: single-run strategy (`balanced`, `aggressive`)
- `--qbraid-environment`: single-run environment (`hardware`, `aer`, `clifford`, `cloud`)
- `--qbraid-shots`: per-iteration shots used in `cloud` mode (default: 1024)

### Matrix benchmarking options

- `--benchmark-executors`: executors to compare (default: `qbraid`)
- `--benchmark-qiskit-modes`: Qiskit modes to compare
- `--benchmark-qbraid-strategies`: qBraid strategies to compare
- `--benchmark-qbraid-environments`: qBraid environments to compare

## Logging Behavior

Executor internals emit Python `logging` records under terse, configuration-aware logger names, for example:

- `ex.qk.clifford.<backend>`
- `ex.qb.aggressive.aer.<backend>`

CLI summary/status output still uses `print`, so executor logs and top-level CLI output are easy to distinguish.

When stderr is a TTY, executor log messages are colorized by log level.
