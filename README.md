# Quantum Hackathon: Wildfire Mitigation with QAOA

This repository holds our hackathon submission. The project frames a wildfire mitigation question as a combinatorial optimization problem and solves it with a Quantum Approximate Optimization Algorithm (QAOA) pipeline that can run on Qiskit simulators, qBraid environments, and real IBM hardware.

The short version of the idea: given a map of dry brush and a fixed budget of Toyon shrubs, where should the shrubs go so that the fewest pairs of adjacent brush cells remain next to each other? Each Toyon plant slows the spread of fire, so breaking up brush clusters is the goal.

## Where to read next

Everything you need to understand, reproduce, and evaluate the work lives under [`docs/`](docs/). Start at the top of that list and walk down.

1. [Problem statement and cost function](docs/problem.md)
2. [QAOA circuit derivation](docs/qaoa.md)
3. [Code architecture and pipeline](docs/architecture.md)
4. [Running the benchmark](docs/running.md)
5. [Process log: what we tried and why](docs/process.md)
6. [Results and how to reproduce them](docs/results.md)

## Thirty second quick start

Install dependencies with `uv sync`, then run a small wildfire instance on the local Clifford simulator:

```bash
uv sync
uv run python src/main.py --problem wildfire --grid-rows 6 --grid-cols 6 --shrub-budget 6 --wildfire-seed 42
```

The run prints the random graph seed, the circuit depth, every optimizer iteration, and a final fire break score. A 2D risk map and a 3D PyVista scene open automatically unless you pass `--headless`.

For hardware runs, credentials, qBraid cloud mode, and matrix benchmarking, see [docs/running.md](docs/running.md).

## Repository map

```
src/
  main.py                      entry point and composition root
  Grid.py                      random graph and QAOA layer builder (the circuit the project now uses)
  problems/wildfire/           wildfire problem model, loss, and postprocessing
  problems/maxcut_problem/     a smaller benchmark used for comparison
  executors/                   Qiskit and qBraid execution backends
  optimizers/                  SPSA and SciPy optimization backends
  dashboard.py                 live matrix benchmarking view
  plot_wildfire_3d.py          standalone 3D scene renderer
results/                       captured run artifacts (images, summaries)
docs/                          the full writeup
assets/                        3D models used by the PyVista scene
```

## Team notes

The `src/GPTCircuit*.py` files are earlier circuit prototypes kept for reference. The active ansatz is the one built by `Grid.BuildQuantumCircuit` in [src/Grid.py](src/Grid.py), which [src/problems/wildfire/problem.py](src/problems/wildfire/problem.py) now calls.
