# Quantum Hackathon MaxCut Benchmark

This project benchmarks a MaxCut-style optimization workflow with a dependency-injected structure:

- `src/problems/maxcut.py` contains the Max-Cut problem implementation
- `src/problems/maxcut_model.py` contains extracted Max-Cut domain/model logic
- `src/executors/qiskit_executor.py` contains the original Qiskit runtime executor
- `src/executors/qbraid_executor.py` contains the qBraid-focused executor (still using Qiskit providers/environments)
- `src/main.py` owns matrix orchestration and cross-combination benchmark comparison logic

The benchmark supports three runtime modes:

- `hardware`: run on a real IBM Quantum backend
- `aer`: run on an Aer simulator seeded from an IBM backend configuration
- `clifford`: run locally on the Aer stabilizer simulator using Clifford-compatible parameter snapping

## Usage

Run the default executor (`qiskit`) directly:

```bash
python src/main.py --mode aer
```

Examples:

```bash
python src/main.py --mode hardware --backend ibm_rensselaer
python src/main.py --mode aer --backend ibm_rensselaer
python src/main.py --mode clifford --num-nodes 120 --reps 3
python src/main.py --executor qbraid --qbraid-strategy aggressive --qbraid-environment aer --num-nodes 60
python src/main.py --run-matrix --benchmark-executors qbraid --benchmark-qbraid-strategies balanced aggressive --benchmark-qbraid-environments aer clifford --num-nodes 60
python src/main.py --run-matrix --benchmark-executors qiskit qbraid --benchmark-qiskit-modes clifford --benchmark-qbraid-strategies balanced aggressive --benchmark-qbraid-environments aer clifford --num-nodes 60
```

## Options

The CLI merges problem and executor options into one parser:

- Global options
  - `--problem`: selects the problem implementation (`maxcut`)
  - `--executor`: selects the executor implementation (`qiskit` or `qbraid`) for single-run mode
  - `--run-matrix`: run all selected executor/option combinations
  - `--benchmark-executors`: executors included in matrix mode

- Problem options
  - `--num-nodes`: graph size
  - `--num-qubits`: ansatz width
  - `--graph-probability`: random graph edge probability
  - `--seed`: random seed
  - `--reps`: ansatz repetitions
- Executor options
  - `--mode`: selects the execution backend
  - `--backend`: IBM backend name used for `hardware` and `aer`
  - `--maxiter`: COBYLA iteration limit

When `--executor qbraid` is selected, qBraid-specific options are available:

- `--qbraid-strategy`: compilation strategy for single-run mode (`balanced`, `aggressive`)
- `--qbraid-environment`: execution environment for single-run mode (`aer`, `clifford`)

In matrix mode, top-level CLI options expand qBraid combinations:

- `--benchmark-qbraid-strategies`: strategy list to expand
- `--benchmark-qbraid-environments`: environment list to expand

The framework compares benchmarking metrics only when all selected combinations expose the same `benchmark_topics` set. `qiskit` provides no benchmark topics, so mixed `qiskit + qbraid` matrices still run and list all results, but skip topic-based benchmark comparison.

For topic-compatible combinations, the framework evaluates tradeoffs between:

- output quality (`cut_size` when available, otherwise inverse final loss)
- compiled resource cost (depth, total ops, 2-qubit ops, transpile time)
- quality/cost tradeoff score (`quality_score / compiled_resource_cost`)

## Notes

- `hardware` and `aer` modes require IBM Quantum credentials to be available through your saved account or `.env` configuration.
- `qiskit-ibm-runtime` can load an account from environment variables. Set:
  - `QISKIT_IBM_CHANNEL` (`ibm_cloud` or `ibm_quantum_platform`)
  - `QISKIT_IBM_TOKEN` (IBM Cloud API key)
  - `QISKIT_IBM_INSTANCE` (CRN or service name)
- `clifford` mode does not require IBM credentials.
- The Clifford mode snaps parameters to multiples of `pi/2` so the stabilizer simulator can evaluate the circuit.
