# QAOA Circuit Derivation

This document walks through how the wildfire cost function turns into the circuit that `Grid.BuildQuantumCircuit` emits. The math follows the notes the team wrote during the hackathon. The exposition fills in the steps that notes tend to skip.

## What QAOA is trying to do

QAOA is a recipe for approximating the ground state of a diagonal cost Hamiltonian `H_C`. You prepare a simple starting state, then alternate two unitaries

```
U(gamma, beta) = exp(-i beta H_M) exp(-i gamma H_C)
```

for `p` rounds, each with its own `gamma_l` and `beta_l`. A classical optimizer twists the angles to minimize the expectation value of `H_C` on the final state. The mixer `H_M` is chosen to move probability amplitude between feasible bit strings. Larger `p` gives better approximations at the cost of depth. We use `p = reps`, set by `--layer-reps`.

The art is in picking `H_C` and `H_M` so that both unitaries are easy to compile and so that the mixer does not leak probability outside the feasible set.

## From QUBO to a Pauli Hamiltonian

The wildfire QUBO from [docs/problem.md](problem.md) is

```
C(x) = sum_{(i, j) in E} (1 - x_i)(1 - x_j) + (k - sum_i x_i)^2
```

We now substitute `x_i = (1 - Z_i) / 2`. The operator `Z_i` reads the spin value of qubit `i`: `Z|0> = +|0>` and `Z|1> = -|1>`. Pushing that through the first factor,

```
1 - x_i = 1 - (1 - Z_i) / 2 = (1 + Z_i) / 2
```

so each edge contributes

```
(1 - x_i)(1 - x_j) = (1 + Z_i)(1 + Z_j) / 4
                   = (1 + Z_i + Z_j + Z_i Z_j) / 4
```

The `1` on its own is a constant. A constant in the Hamiltonian produces a global phase under `exp(-i gamma H_C)`, and global phases do not affect measurement probabilities, so we drop it.

That leaves three kinds of operators summed over the edge set: single `Z_i`, single `Z_j`, and two body `Z_i Z_j`. Each edge contributes a `Z` on both of its endpoints, so after summing over all edges the total coefficient on `Z_i` is proportional to the degree of vertex `i`. In the code we do not actually compute the degree. We fold the single qubit contribution into a pass of `Rz` rotations in the ansatz, and the two qubit contribution into one `Rzz` per edge. Because `Rz` rotations commute with each other, the single qubit pass lands in the same place whether we think of it as one rotation per incident edge or a single rotation with combined angle.

The code in `Grid.BuildQAOALayer` implements the two qubit part directly:

```python
for (i, j) in self.edges:
    qc.rzz(-2 * gamma, i, j)
```

The factor of `-2` on the angle matches the Qiskit convention where `Rzz(theta)` applies `exp(-i theta ZZ / 2)`. To get `exp(-i gamma ZZ)` we ask for `Rzz(2 gamma)`. The leading minus sign flips the optimization from "maximize bad adjacencies" to "minimize them", which is what we want.

The single qubit `Z` pass is absent from the current implementation. Dropping it is equivalent to shifting the cost function by a term that depends only on the Hamming weight of the solution. Because the mixer we use preserves Hamming weight (see below), that shift is a global phase on every state the circuit can reach, and the optimizer does not notice it. Keeping the circuit shorter is more valuable to us than carrying a term that cancels out.

## The budget constraint and the choice of mixer

The second term in the QUBO, `(k - sum_i x_i)^2`, is what would normally force the solver to use exactly `k` shrubs. Encoding it directly would produce a dense set of `ZZ` couplings between every pair of qubits, and the resulting circuit would be very deep.

We avoid that entirely. Instead of penalizing the wrong Hamming weight in the cost, we prevent the circuit from ever moving to the wrong Hamming weight in the first place. The trick is the mixer.

The standard QAOA mixer is a transverse field, `H_M = sum_i X_i`. It moves amplitude between any two bit strings that differ in a single bit, so it does not preserve Hamming weight. Flipping that out for an `XY` mixer gives exactly what we need:

```
H_M = sum_{(i, j) in edges} (X_i X_j + Y_i Y_j)
```

`XX + YY` is the hopping term from the one dimensional `XY` model. It swaps `|01>` with `|10>` but leaves `|00>` and `|11>` alone. Every term in that sum commutes with the total number operator `sum_i (1 - Z_i) / 2`, so the whole mixer lives inside the Hamming weight `k` subspace. If we start the circuit on a bit string with exactly `k` ones, the mixer can only take us to other bit strings with exactly `k` ones. The budget constraint is enforced by construction.

There is one more piece: the starting state. A Hadamard on every qubit produces a uniform superposition over all `2^n` bit strings, which is not what we want because most of those have the wrong Hamming weight. Instead we apply an `X` to the first `budget` qubits. That gives us a single basis state `|1...1 0...0>` with exactly `k` ones. The mixer then spreads amplitude across the feasible subspace as the layers run.

`Grid.BuildQuantumCircuit` does precisely that:

```python
qc.x(range(self.budget))
```

## Compiling the mixer

`exp(-i beta (XX + YY))` is a two qubit unitary. The Qiskit library ships the two components separately as `Rxx` and `Ryy`, and because `XX` commutes with `YY` on the same pair, we can apply them back to back without a Trotter error:

```python
qc.rxx(-beta, i, (i + 1) % num_qubits)
qc.ryy(-beta, i, (i + 1) % num_qubits)
```

The minus sign again follows the Qiskit convention, and the combination gives the right rotation inside each `|01>, |10>` subspace. Because the mixer is defined on a sum over edges, the layer applies it to every edge.

`BuildQAOALayer` walks the qubit indices in two passes, first even starts and then odd starts, so that adjacent two qubit gates never act on the same qubit in the same pass. That pattern is friendly to hardware schedulers that can run disjoint gates in parallel.

## The full layer in order

`BuildQuantumCircuit` stacks the following for each `(gamma_l, beta_l)` pair:

```
1. Cost unitary
   for each edge (i, j) in the grid induced subgraph:
     Rzz(-2 gamma_l) on (i, j)
   barrier

2. Mixer unitary
   even pass:  Rxx(-beta_l), Ryy(-beta_l) on pairs (0,1), (2,3), ...
   odd pass:   Rxx(-beta_l), Ryy(-beta_l) on pairs (1,2), (3,4), ...
   barrier
```

Barriers are inserted to keep the transpiler from fusing layers across the boundary. They have no effect on the final state, only on how the passes lay out the gates.

The bit string initialization happens once, outside the layer loop:

```python
qc.x(range(self.budget))
```

and the whole circuit is `p` copies of the layer stacked on top of that.

## Why this matches the hackathon notes

The notes wrote the derivation in the order we would reason about it at the whiteboard: substitute `Z`, spot the constants, fold the singletons into `Rz` passes, and handle the edge terms as `Rzz`. The code does the same thing minus the single `Z` pass, because that pass is an irrelevant phase once the mixer fixes the Hamming weight. The notes also call out the mixer choice and why we did not implement the budget penalty directly. That line of reasoning is what `Grid.BuildQuantumCircuit` realises. The file is worth reading alongside this document; it is short and maps line for line onto the steps above.

## Parameter plumbing

The ansatz is returned to Qiskit with symbolic `ParameterVector` objects as the `gamma` and `beta` values. Qiskit's parameter arithmetic lets us write `-2 * gamma_l` and `-beta_l` with plain Python operators, and Qiskit keeps the symbolic form until the estimator binds numbers at run time. Binding happens inside the executor, which passes one pair of floats per layer to the estimator every time the optimizer asks for a loss evaluation.

## Reading the result

The executor returns a per qubit expectation value map. `WildfireModel.exp_map_to_shrub_scores` turns those `<Z>` values into probabilities of being a shrub by the identity `<1 - Z> / 2`, clipped to `[0, 1]`. `choose_shrub_sites` then sorts by score and keeps the top `budget` qubits. The resulting bit string is the recommended shrub placement. Those sites feed `calc_fire_break_score`, which counts the edges the placement breaks, and that score is the number the benchmark summary reports.
