# Running the Benchmark

This document is the operator's manual. It covers installation, credentials, single runs, matrix mode, and every CLI flag that matters. For background on what the code is doing, read [docs/problem.md](problem.md), [docs/qaoa.md](qaoa.md), and [docs/architecture.md](architecture.md) first.

## Installing

The project uses `uv` for environments and lockfile sync. From the repository root:

```bash
uv --version          # confirm uv is installed
uv sync               # create .venv and install from uv.lock
uv run python src/main.py --help
```

`uv sync` is idempotent. Running it a second time is a no op if nothing has changed.

## Credentials

`clifford` mode needs nothing. `aer` and `hardware` modes read IBM Quantum credentials from a `.env` file at the repository root:

```
QISKIT_IBM_CHANNEL=ibm_cloud
QISKIT_IBM_TOKEN=your_token_here
QISKIT_IBM_URL=https://cloud.ibm.com
QISKIT_IBM_INSTANCE=your_crn_or_service_name
```

qBraid Cloud mode needs one extra line in the same file:

```
QBRAID_API_KEY=your_qbraid_api_key
```

`.env` is loaded by `python-dotenv` the first time an executor tries to build an IBM or qBraid runtime, so the same file works for every subcommand.

## A first run

Start with a small wildfire instance on the local Clifford simulator. It finishes in a few seconds and exercises the whole pipeline.

```bash
uv run python src/main.py \
  --problem wildfire \
  --grid-rows 6 --grid-cols 6 \
  --shrub-budget 6 \
  --wildfire-seed 42 \
  --layer-reps 2
```

What you should see:

1. A log line from `WildfireModel` that includes the seed and the random graph shape. That line confirms the `build_random_grid` helper picked the right subgraph.
2. A circuit build line from `Grid.BuildQuantumCircuit` that reports the qubit count, parameter count, depth, and seed.
3. One log line per SPSA iteration, with `gamma`, `beta`, loss, and wall time.
4. A results summary block printed by `main.py` with the chosen combination, fire break score, and final loss.
5. A non blocking Matplotlib window showing the risk map and the chosen shrub placements, plus a PyVista 3D scene with little tree models on the chosen cells. Add `--headless` to skip both.

## Wildfire flags

All of these are registered in `WildfireMitigationProblem.add_cli_arguments`:

```
--grid-rows INT              rows of the base grid, default 10
--grid-cols INT              columns of the base grid, default 10
--shrub-budget INT           number of Toyon plants to place, default 10
--brush-probability FLOAT    chance a cell starts as dry brush, default 0.7
--wildfire-seed INT          random seed for the bush layout, default 42
--layer-reps INT             QAOA repetitions, default 2
--headless                   disable the 2D and 3D visualization windows
```

`--brush-probability` sets the density of the induced subgraph. Lower values give fewer qubits and a faster run. `--wildfire-seed` is the only source of non determinism in the problem build; the same seed produces the same random graph every time.

## Optimizer flags

In `auto` mode the wildfire pipeline picks SPSA. You can force either backend by hand:

```
--optimizer-backend {auto, scipy, spsa}
--maxiter INT                shared alias for iteration budget
--spsa-maxiter INT           SPSA evaluation budget, default 20
--spsa-learning-rate FLOAT   base SPSA learning rate, default 0.2
--spsa-perturbation FLOAT    base SPSA perturbation, default 0.1
--spsa-alpha FLOAT           SPSA learning rate decay, default 0.602
--spsa-gamma FLOAT           SPSA perturbation decay, default 0.101
```

SciPy accepts the usual COBYLA and Nelder–Mead configuration; see `src/optimizers/scipy_optimizer.py`.

## Qiskit executor flags

```
--executor qiskit
--mode {hardware, aer, clifford}       default aer
--backend NAME                         IBM backend name for hardware and aer
```

`clifford` ignores the backend. `aer` uses the backend's noise model, if one is configured, and `hardware` actually ships the circuit to IBM Runtime. A typical local run looks like this:

```bash
uv run python src/main.py --executor qiskit --mode clifford --grid-rows 10 --grid-cols 10 --shrub-budget 10
```

## qBraid executor flags

```
--executor qbraid
--qbraid-strategy {balanced, aggressive}
--qbraid-environment {hardware, aer, clifford, cloud}
--qbraid-shots INT                     shots per iteration in cloud mode, default 1024
--backend NAME                         IBM backend name or qBraid device id
```

qBraid cloud mode is the slowest and the only one that talks to the qBraid API. Example:

```bash
uv run python src/main.py \
  --executor qbraid \
  --qbraid-strategy balanced \
  --qbraid-environment cloud \
  --backend <qbraid_device_id> \
  --qbraid-shots 2048 \
  --grid-rows 10 --grid-cols 10 --shrub-budget 10
```

## Matrix benchmarking

Matrix mode runs every combination of the options you list and then prints a comparison table. It is the way to explore quality and cost tradeoffs.

```bash
uv run python src/main.py \
  --run-matrix \
  --benchmark-executors qbraid \
  --benchmark-qbraid-strategies balanced aggressive \
  --benchmark-qbraid-environments clifford aer \
  --grid-rows 10 --grid-cols 10 \
  --shrub-budget 10 \
  --layer-reps 2
```

The wildfire matrix run opens the live dashboard automatically so you can watch the iterations roll in. It also writes a final dashboard image to `src/benchmark_result.png`.

Mixed matrix runs also work:

```bash
uv run python src/main.py \
  --run-matrix \
  --benchmark-executors qiskit qbraid \
  --benchmark-qiskit-modes clifford aer \
  --benchmark-qbraid-strategies balanced aggressive \
  --benchmark-qbraid-environments clifford aer \
  --grid-rows 10 --grid-cols 10 \
  --shrub-budget 10
```

## Standalone 3D scene

Occasionally we want a rendered wildfire scene without running a full optimization. [src/plot_wildfire_3d.py](../src/plot_wildfire_3d.py) loads the same problem setup and renders a PyVista scene with three rotating tree models from `assets/kenney_nature-kit`:

```bash
uv run python src/plot_wildfire_3d.py --grid-rows 10 --grid-cols 10 --shrub-budget 10
uv run python src/plot_wildfire_3d.py --grid-rows 10 --grid-cols 10 --shrub-budget 10 --save-image outputs/wildfire_3d.png
```

## Reading the logs

Each executor writes to a logger named after its configuration. Examples:

```
ex.qk.clifford.ibm_rensselaer
ex.qk.aer.ibm_rensselaer
ex.qb.aggressive.cloud.<device_id>
```

Log lines include the run phase (`Setup`, `Build and optimize circuit`, `Optimize`), timing blocks, the iteration loss, and the seed. `main.py` still uses `print` for the final combination summary so that high level output stays distinct from executor chatter. When stderr is a TTY, log levels are colorised.

## Reproducing a specific run

Every wildfire run logs its seed on the first line. To reproduce a run, copy the seed into `--wildfire-seed`, and copy the grid size, shrub budget, and brush probability from the CLI you are comparing against. The random graph and the starting parameters are fully determined by those inputs.
