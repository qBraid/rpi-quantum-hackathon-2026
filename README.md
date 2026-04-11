# Quantum Hackathon MaxCut Benchmark

This project benchmarks a MaxCut-style optimization workflow with a dependency-injected structure:

- `src/problems/maxcut.py` contains the Max-Cut problem implementation
- `src/executors/qiskit_executor.py` contains the Qiskit-based runtime executor
- `src/main.py` composes both CLIs and runs the selected problem through the selected executor

The benchmark supports three runtime modes:

- `hardware`: run on a real IBM Quantum backend
- `aer`: run on an Aer simulator seeded from an IBM backend configuration
- `clifford`: run locally on the Aer stabilizer simulator using Clifford-compatible parameter snapping

## Usage

Run the CLI directly:

```bash
python src/main.py --mode aer
```

Examples:

```bash
python src/main.py --mode hardware --backend ibm_rensselaer
python src/main.py --mode aer --backend ibm_rensselaer
python src/main.py --mode clifford --num-nodes 120 --reps 3
```

## Options

The CLI merges problem and executor options into one parser:

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

## Notes

- `hardware` and `aer` modes require IBM Quantum credentials to be available through your saved account or `.env` configuration.
- `clifford` mode does not require IBM credentials.
- The Clifford mode snaps parameters to multiples of `pi/2` so the stabilizer simulator can evaluate the circuit.
