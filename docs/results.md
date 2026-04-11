# Results

This page covers where run artefacts live, how to read them, and how to reproduce the headline numbers. Every captured result was produced by `src/main.py`, so the recipe for reproducing one is always a single command plus the seed that was logged.

## Where artefacts live

The `results/` directory holds captured runs from the hackathon. Each subdirectory is one grid size or one experiment and contains up to four files:

```
convergence.png          loss vs iteration for the run
solver_comparison.png    side by side optimizer comparison
summary.json             run metadata, final metrics, and seed
wildfire_solution.png    the risk map with selected shrub sites overlaid
```

`results_6x6/` is reserved for repeatable smoke tests on a six by six grid. It is the fastest path to a working figure when you need a screenshot.

If you run your own matrix benchmarks, the qBraid dashboard writes a composite image to `src/benchmark_result.png` at the end of the run. That file is clobbered on every run, so copy it somewhere if you want to keep it.

## Reading `summary.json`

Every capture carries a JSON summary with roughly this shape:

```
{
  "problem": "wildfire",
  "optimizer": "spsa(...)",
  "results": [
    {
      "combination": "qbraid(strategy=balanced,environment=clifford)",
      "primary_metric_name": "fire_break_score",
      "primary_metric_value": 14.0,
      "final_loss": 3.2,
      "postprocess": { ... },
      "experiment_results": [ ... ]
    },
    ...
  ],
  "best_result": { ... }
}
```

The `experiment_results` list inside each run is the full iteration history. Each entry has the loss that SPSA saw on that step and the expectation value map that the estimator returned. Rebuilding `convergence.png` from that list is a matter of plotting `loss` against the index. The `postprocess` dictionary has the selected shrub cells, the fuel map, and the risk map, which is what `utils/wildfire_visualization.py` reads to draw `wildfire_solution.png`.

## Reproducing a headline run

Every wildfire run logs its seed on the first line. To reproduce a number from an old summary, copy:

* the seed into `--wildfire-seed`
* the grid size into `--grid-rows` and `--grid-cols`
* the shrub budget into `--shrub-budget`
* the brush probability into `--brush-probability`
* the repetitions into `--layer-reps`

The random graph is deterministic in the seed, the initial SPSA parameters are deterministic in the seed, and the executor transpile path is deterministic in the optimization level. The only source of randomness left is the estimator sampler, and on `clifford` mode there is none because the estimator is exact. Clifford runs are therefore bit identical across machines, which makes them the preferred target for smoke tests.

For example, to rerun a six by six Clifford benchmark that was captured with seed 42:

```bash
uv run python src/main.py \
  --problem wildfire \
  --grid-rows 6 --grid-cols 6 \
  --shrub-budget 6 \
  --brush-probability 0.7 \
  --wildfire-seed 42 \
  --layer-reps 2 \
  --executor qiskit --mode clifford \
  --headless
```

The run should finish in seconds and the fire break score should match the value in the corresponding `summary.json`.

## Headline numbers we watch

When comparing configurations we watch three numbers:

1. `fire_break_score`, which is the reward: total edge weight broken by the chosen shrub set. Higher is better.
2. `final_loss`, which is the QAOA objective value after optimization. Lower is better, and it should trend down over iterations in `convergence.png`.
3. `two_qubit_ops` on the transpiled circuit, which is the cost proxy: gate count is a decent stand in for wall time on real hardware, and it lets us compare strategies without running every one on the actual device.

The matrix mode prints a `COMBINATION SUMMARY` block at the end of every run with all three numbers for every combination, and the best row is called out as `Best result`. That row is what we cite when we write up a benchmark.

## Known gotchas

A Clifford run snaps `gamma` and `beta` to multiples of `pi / 2` so the circuit stays in the Clifford group. That means the loss on a Clifford run lands on a discrete set of values, and the SPSA trajectory looks stair stepped. That is expected. The same run on `aer` or `hardware` produces a continuous loss and a smoother curve.

The `XY` mixer starts the circuit on a bit string with exactly `budget` ones. If you ask for a budget larger than the number of bush qubits, the `build_ansatz` path clips it to `len(grid.bushes)`, and the log line will report the clipped value. The fire break score is still computed against the real chosen set, so the score stays honest even when the budget is clipped.

If a run opens a window you did not want, pass `--headless`. If the matrix dashboard hangs waiting for a PyVista window, close the PyVista scene and the dashboard will finalize.

## What to capture for your own submission

For a fresh submission, we recommend capturing:

* a screenshot or a saved `wildfire_solution.png` from a ten by ten clifford run
* the corresponding `summary.json`
* the final log block that prints the seed, the fire break score, and the SPSA options
* an optional matrix run image from `src/benchmark_result.png`

Four files cover the "what did you do, why did it work, and can we rerun it" question cleanly.
