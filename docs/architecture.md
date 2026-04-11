# Code Architecture

## The shape of the pipeline

The project is laid out so that a problem, an optimizer, and an executor snap together in a single place, and any of the three can be swapped without touching the other two. That place is [src/main.py](../src/main.py), which reads the CLI arguments, picks a class from each category, and calls `run_pipeline`.

At the highest level, one run looks like this:

```
Problem.build_problem_data  ->  dataclass with graph, observables, seed, grid, fuel map
Problem.build_ansatz        ->  parameterised QuantumCircuit
Executor.execute            ->  transpile, prepare estimator, call Optimizer.optimize
Optimizer.optimize          ->  minimise the loss closure built by Problem.make_loss
Problem.postprocess         ->  turn the final expectation map into domain output
```

Everything else in the repo is one of those five stages.

## Problems

The `Problem` base class in [src/problems/base.py](../src/problems/base.py) is an abstract contract. A problem knows how to register its own CLI flags, how to build its static data, how to construct its ansatz, how to describe its parameters for logging, how to build a loss closure, and how to postprocess results.

Two concrete problems live under `src/problems/`. The MaxCut implementation is small and helpful as a smoke test. The wildfire implementation is the hackathon focus and is split into a pure model and an orchestrating class:

* [src/problems/wildfire/model.py](../src/problems/wildfire/model.py) owns the random graph construction, the `WildfireProblemData` dataclass, the observable groups, and helpers that convert `<Z>` expectation values to shrub scores. It imports `Grid` from `src/Grid.py` and uses `build_random_grid` to make the same seeded random layout every time.
* [src/problems/wildfire/problem.py](../src/problems/wildfire/problem.py) wires the model into the framework. It registers the wildfire CLI flags, calls `build_random_grid` again inside `build_ansatz` so the ansatz sees the same bush coordinates as the problem data, delegates the circuit build to `Grid.BuildQuantumCircuit`, and defines the loss closure and postprocess routine.

The loss closure captures the evaluator, expands each `<Z>` map into a vector of shrub scores, sums `(1 - s_i)(1 - s_j)` over the graph edges, and adds the quadratic budget term. It also logs the iteration index, current loss, current `gamma` and `beta`, and iteration time.

## The circuit

[src/Grid.py](../src/Grid.py) is the active ansatz builder. The `Grid` class carries four things:

* the grid dimensions `length` and `width`
* the list of bush coordinates
* a `budget` equal to the number of Toyon shrubs
* an `idx` dictionary that maps a `(row, col)` tuple to the qubit index that represents that bush

`Grid.random` is a constructor that samples a fixed number of bush coordinates. `build_random_grid` in `wildfire/model.py` is a slightly different entry point that uses `numpy.random.default_rng(seed)` to sample a Bernoulli mask and converts it into a bush list, which keeps the sampling in step with the numpy seeds used elsewhere.

`Grid.BuildEdges` walks the bush list and connects any two bushes that sit in neighbouring grid cells. Those edges are the edges of the induced subgraph that the QAOA cost unitary runs over.

`Grid.BuildQAOALayer` is the part that is worth reading alongside [docs/qaoa.md](qaoa.md). It applies one `Rzz(-2 * gamma)` per edge, then two passes of `Rxx(-beta) Ryy(-beta)` on alternating qubit pairs to realise the `XY` mixer.

`Grid.BuildQuantumCircuit` prepends an `X` gate on the first `budget` qubits to seed the uniform Hamming weight `k` state, then composes `reps` copies of the layer with a barrier between each. The return is a plain `QuantumCircuit` whose parameters are the `gamma` and `beta` symbols supplied by the caller.

The earlier prototypes at `src/GPTCircuit.py`, `src/GPTCircuitImproved.py`, `src/GridQuantumCircuit.py`, and `src/LayerOptimizedCircuit.py` are kept in the repo so reviewers can compare. The wildfire problem is no longer wired to any of them. `docs/process.md` explains what each prototype was exploring.

## Executors

[src/executors/qiskit_executor.py](../src/executors/qiskit_executor.py) is the local and IBM path. It supports three modes:

* `clifford` runs the ansatz on the Qiskit Aer stabilizer simulator, after snapping `gamma` and `beta` to multiples of `pi / 2` so the circuit lands in the Clifford group. This is the cheap default.
* `aer` uses the real `AerSimulator`, optionally seeded from the topology of an IBM backend so that the transpiler targets hardware like connectivity.
* `hardware` runs against a real IBM backend through the Qiskit Runtime estimator.

The executor builds the ansatz, transpiles it at optimization level 3, binds the observables the problem exposes, and hands the resulting evaluator to the optimizer. Every iteration the estimator returns a fresh map of `<Z_i>`, which the wildfire loss closure converts into a cost.

[src/executors/qbraid_executor.py](../src/executors/qbraid_executor.py) is the second path. It runs through qBraid's compilation stack and can reach hardware, Aer, Clifford, and qBraid Cloud backends. It exposes two compilation strategies: `balanced` trades quality and speed, while `aggressive` squeezes gate count harder. The matrix mode in `main.py` uses this executor to compare strategies and environments, and the live dashboard in [src/dashboard.py](../src/dashboard.py) plots the results as they arrive.

## Optimizers

Two optimizer backends live under `src/optimizers/`. SPSA is the default for wildfire runs because the loss is expensive and noisy, and SPSA gets by on two evaluations per step instead of one per parameter. SciPy's COBYLA and Nelder–Mead drive the smaller MaxCut runs and work fine when the loss is cheap. Both obey the same abstract `Optimizer` contract and both accept a seed so that initial parameters are reproducible.

The optimizer receives a callable from `Problem.make_loss` and a starting vector seeded from the problem's random seed. It returns an `OptimizerResult` that the executor logs and forwards to `Problem.postprocess`.

## Run artefacts

`executor.execute` returns a dictionary with runtime labels, timings, primary metric, cut size, the full `postprocess` payload, and the list of per iteration records. `main.py` prints a combination summary, optionally writes a dashboard image for qBraid matrix runs, and returns everything to the caller. Captured historical runs live under [results/](../results/).

## How the pieces know about the same random graph

A subtle point worth calling out: the problem data and the ansatz are built by two different method calls, and neither one takes the other as an argument. They both have to produce the same random subgraph. The fix is to put the seeded sampling inside a pure helper, `build_random_grid`, and have both callers invoke it with the same seed. As long as numpy's default generator is deterministic for a given seed, both copies of the `Grid` come out identical, their edge lists line up, and the qubit indices used in the observables match the ones the ansatz was built from. The seed itself is passed from the `WildfireMitigationProblem` dataclass, which stores it verbatim from the `--wildfire-seed` flag. Every run logs the seed at the start so that reproducing a run is a matter of copying the number from the logs.
