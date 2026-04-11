# Quantum Hackathon Benchmark Suite

This project benchmarks two optimization workflows with a dependency-injected structure:

- `src/problems/maxcut_problem/` contains the relocated Max-Cut problem implementation
- `src/problems/wildfire/` contains the wildfire mitigation problem based on the layer-optimized circuit layout
- `src/executors/qiskit_executor.py` contains the Qiskit runtime executor
- `src/executors/qbraid_executor.py` contains the qBraid-focused executor (including qBraid cloud mode via `QbraidProvider`)
- `src/main.py` owns matrix orchestration and cross-combination benchmark comparison logic

The benchmark supports four runtime modes:

- `hardware`: run on a real IBM Quantum backend
- `aer`: run on an Aer simulator seeded from an IBM backend configuration
- `clifford`: run locally on the Aer stabilizer simulator
- `cloud`: run on qBraid Quantum Cloud using a qBraid device ID

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

### 4) (Optional) Activate the venv manually

If you prefer an activated shell instead of `uv run`:

```bash
source .venv/bin/activate
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

### 5b) Configure qBraid cloud credentials (for `qbraid --qbraid-environment cloud`)

Set `QBRAID_API_KEY` in your shell or `.env` file.

```bash
export QBRAID_API_KEY=your_qbraid_api_key
```

If using `.env`, add:

```bash
cat >> .env <<'EOF'
QBRAID_API_KEY=your_qbraid_api_key
EOF
```

Cloud mode reads `--backend` as a qBraid device ID (not an IBM backend name).

### 6) Verify CLI wiring

```bash
uv run python src/main.py --help
```

## Running Benchmarks

### Single-run examples

```bash
uv run python src/main.py --executor qiskit --mode clifford --num-nodes 60
uv run python src/main.py --executor qiskit --mode aer --backend ibm_rensselaer --num-nodes 60
uv run python src/main.py --executor qbraid --qbraid-strategy balanced --qbraid-environment hardware --backend ibm_rensselaer --num-nodes 60
uv run python src/main.py --executor qbraid --qbraid-strategy aggressive --qbraid-environment aer --num-nodes 60
uv run python src/main.py --executor qbraid --qbraid-environment cloud --qbraid-strategy balanced --backend <qbraid_device_id> --qbraid-shots 2048 --num-nodes 60
uv run python src/main.py --problem wildfire --executor qiskit --mode clifford --grid-rows 10 --grid-cols 10 --shrub-budget 10
```

Minimal qBraid cloud example:

```bash
uv run python src/main.py --executor qbraid --qbraid-environment cloud --backend <qbraid_device_id>
```

### qBraid comparison matrix (recommended)

Compare at least two compile strategies across at least two environments:

```bash
uv run python src/main.py \
  --run-matrix \
  --benchmark-executors qbraid \
  --benchmark-qbraid-strategies balanced aggressive \
  --benchmark-qbraid-environments hardware aer clifford cloud \
  --num-nodes 60 \
  --num-qubits 10 \
  --reps 2
```

### Mixed qiskit + qbraid matrix

```bash
uv run python src/main.py \
  --run-matrix \
  --benchmark-executors qiskit qbraid \
  --benchmark-qiskit-modes clifford \
  --benchmark-qbraid-strategies balanced aggressive \
  --benchmark-qbraid-environments hardware aer clifford cloud \
  --num-nodes 60
```

Note: mixed matrices still run and list all combinations. Topic-based benchmark comparison is only performed when all combinations expose the same `benchmark_topics` set.

## Options

- Global options
  - `--problem`: selects the problem implementation (`maxcut`, `wildfire`)
  - `--executor`: selects the executor implementation (`qiskit` or `qbraid`) for single-run mode
  - `--run-matrix`: run all selected executor/option combinations
  - `--benchmark-executors`: executors included in matrix mode

- Problem options
  - MaxCut: `--num-nodes`, `--num-qubits`, `--graph-probability`, `--seed`, `--reps`
  - Wildfire: `--grid-rows`, `--grid-cols`, `--shrub-budget`, `--brush-probability`, `--wildfire-seed`, `--layer-reps`

- MaxCut options
  - `--num-nodes`: graph size
  - `--num-qubits`: ansatz width
  - `--graph-probability`: random graph edge probability
  - `--seed`: random seed
  - `--reps`: ansatz repetitions

- Wildfire options
  - `--grid-rows`: grid row count
  - `--grid-cols`: grid column count
  - `--shrub-budget`: Toyon shrub budget
  - `--brush-probability`: chance that a cell starts as dry brush
  - `--wildfire-seed`: random seed for landscape generation
  - `--layer-reps`: layer-optimized circuit repetitions

- Qiskit executor options
  - `--mode`: execution backend (`hardware`, `aer`, `clifford`)
  - `--backend`: IBM backend name used for `hardware` and `aer`
  - `--maxiter`: COBYLA iteration limit

- qBraid executor options
  - `--qbraid-strategy`: single-run strategy (`balanced`, `aggressive`)
  - `--qbraid-environment`: single-run environment (`hardware`, `aer`, `clifford`, `cloud`)
  - `--qbraid-shots`: per-iteration shots used in `cloud` mode
  - `--benchmark-qbraid-strategies`: matrix strategies
  - `--benchmark-qbraid-environments`: matrix environments

## Logging Behavior

Executor internals emit Python `logging` records under terse, configuration-aware logger names, for example:

- `ex.qk.clifford.<backend>`
- `ex.qb.aggressive.aer.<backend>`

CLI summary/status output still uses `print`, so executor logs and top-level CLI output are easy to distinguish.

When stderr is a TTY, executor log messages are colorized by log level.
