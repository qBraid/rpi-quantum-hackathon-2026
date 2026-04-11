# Quantum Hackathon MaxCut Benchmark

This project benchmarks a MaxCut-style optimization workflow with a dependency-injected structure:

- `src/problems/maxcut.py` contains the Max-Cut problem implementation
- `src/problems/maxcut_model.py` contains extracted Max-Cut domain/model logic
- `src/executors/qiskit_executor.py` contains the original Qiskit runtime executor
- `src/executors/qbraid_executor.py` contains the qBraid-focused executor (still using Qiskit providers/environments)
- `src/main.py` composes problem + executor CLIs and dispatches using `--problem` and `--executor`

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
python src/main.py --executor qbraid --qbraid-strategies balanced aggressive --qbraid-environments aer clifford --num-nodes 60
```

## Options

The CLI merges problem and executor options into one parser:

- Global options
  - `--problem`: selects the problem implementation (`maxcut`)
  - `--executor`: selects the executor implementation (`qiskit` or `qbraid`)

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

- `--qbraid-strategies`: compilation strategies to compare (`balanced`, `aggressive`)
- `--qbraid-environments`: execution environments to compare (`aer`, `clifford`)

The qBraid executor compares at least two compilation strategies across at least two execution environments and reports tradeoffs between:

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
