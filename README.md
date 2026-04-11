# Quantum Hackathon MaxCut Benchmark

This project benchmarks a MaxCut-style optimization workflow with three runtime modes:

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
python src/main.py --mode clifford
```

## Options

- `--mode`: selects the execution backend
- `--backend`: IBM backend name used for `hardware` and `aer`
- `--num-nodes`: graph size
- `--num-qubits`: ansatz width
- `--graph-probability`: random graph edge probability
- `--maxiter`: COBYLA iteration limit
- `--seed`: random seed
- `--reps`: ansatz repetitions

## Notes

- `hardware` and `aer` modes require IBM Quantum credentials to be available through your saved account or `.env` configuration.
- `clifford` mode does not require IBM credentials.
- The Clifford mode snaps parameters to multiples of `pi/2` so the stabilizer simulator can evaluate the circuit.

