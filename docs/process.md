# Process Log: What We Tried

This is the rough history of how the implementation ended up where it is. It covers ideas we kept, ideas we threw out, and a few dead ends that were educational enough to write down. The goal is to give a reviewer the context that git history alone does not carry.

## Starting point

We began with the cost function straight from the hackathon prompt: a grid of dry brush cells, a budget of Toyon shrubs, and the goal of minimizing surviving brush to brush adjacencies. On paper that is a weighted minimum vertex cover flavoured QUBO. The first question we argued about was whether to compile it with a standard QAOA mixer plus a Lagrangian budget penalty, or to use a Hamming weight preserving mixer and skip the penalty entirely. We chose the second path, for reasons spelled out in [docs/qaoa.md](qaoa.md). The short version: a Lagrangian penalty produces a dense cost unitary and fights the solver for influence, while an `XY` mixer enforces the budget exactly by construction.

## Circuit prototypes

Four circuit prototypes live in the repository. Each was built while we were learning the problem, and each taught us something different.

`src/GPTCircuit.py` was the first pass. It implemented the naive "cost plus Lagrangian" layout. It produced a circuit that was correct in principle but deep enough that the optimizer lost traction on anything past a four by four grid. We kept it as a baseline.

`src/GPTCircuitImproved.py` was the version the wildfire problem was wired to for most of the hackathon. It builds the cost unitary as a sequence of `X; CX; Rz; CX; X` gadgets that apply a phase to the `|00>` state of each edge, which is the exact form the expanded cost term asks for. It splits the edges into an even and an odd pass so that gates in the same pass touch disjoint qubit pairs, and it uses `Rxx` and `Ryy` for the `XY` mixer. This is the circuit that taught us the value of the parity split pattern. The downside is that it targets the full `rows * cols` lattice, whether or not a given cell actually contains brush.

`src/GridQuantumCircuit.py` was an experiment in treating the cost unitary as a flat list of edge gadgets with no parity split, to see whether the transpiler could schedule it better on its own. It could not, at least not at depth that mattered, and we went back to explicit parity groups.

`src/LayerOptimizedCircuit.py` was an experiment in sharing rotations between layers, inspired by layer reduction tricks from QAOA literature. It worked but it made the code harder to reason about, so we shelved it.

The circuit we ship is the one in [src/Grid.py](../src/Grid.py). It is simpler than `GPTCircuitImproved` because it assumes the cost unitary only cares about edges that actually exist in the induced subgraph, which is exactly what the problem wants. It also keeps the same parity trick for the mixer. The key switch was moving the graph structure out of the circuit builder and into a separate `Grid` class, so that the same object is the source of truth for edges, qubit indices, and the starting bit string.

## The random graph switch

The turning point for the wildfire problem was realising that the lattice model overstates the problem. If we generate a fuel map with brush density `p`, only about `p * rows * cols` cells are actually brush. All the other cells are irrelevant to the cost function. Running QAOA on every lattice qubit was wasting a lot of space on empty land.

Switching the wildfire pipeline to use `Grid.random` sized the circuit to the real problem and matched what the hackathon prompt asks for in the first place. It also made the seed reproducibility story much simpler: pick a seed, sample a bush layout, build a graph, build a circuit against that graph, and log the seed so anyone can reproduce it. That refactor touched `wildfire/model.py`, `wildfire/problem.py`, and introduced the shared `build_random_grid` helper that both `build_problem_data` and `build_ansatz` call with the same seed. The problem data and the ansatz are guaranteed to see the same subgraph because the helper is pure and deterministic for a given seed.

While we were in there we added a `grid` field to `WildfireProblemData` so that `postprocess` can map qubit indices back to the original `(row, col)` coordinates without replaying the sampling, and we added a seed log line to every major stage so that a reviewer can scan a log and know exactly which random graph produced the numbers.

## Optimizer choices

We ran the small grids through SciPy's Nelder–Mead first because it is cheap to set up. It was fine at four by four but started to wander on larger grids because the loss surface picked up noise from the sampled edge set. SPSA is the standard answer to that, and swapping it in stabilized the optimization at depth `reps = 2` on six by six and ten by ten grids. The SPSA defaults in the repo are tuned for wildfire. For MaxCut we kept SciPy because its loss is cheap and smooth.

## Hardware and cloud

We smoke tested the pipeline on `ibm_rensselaer` through Qiskit Runtime and on qBraid Cloud devices. Running on real hardware surfaced one issue that the simulators hid: the transpiler was happy to collapse our parity split passes if we forgot to insert the barrier between them, which produced gate schedules that did not respect connectivity. Adding an explicit `barrier` after each pass in `BuildQAOALayer` fixed it.

The matrix benchmarking mode came out of the hardware work. Rather than babysitting individual runs, we wanted a single command that would sweep qBraid strategies and environments, collect metrics, and report the best quality and cost tradeoff. The live dashboard in `src/dashboard.py` grew out of wanting to watch those runs without babysitting a terminal.

## Things we considered and dropped

We considered weighted edges driven by a `risk_map`, so that breaking adjacencies near a road or a building would be worth more. The code still carries the `risk_map` and `edge_weights` structure. We left the current loss with uniform weights so that the math lines up exactly with the hackathon write up and so that comparing runs is one fewer moving part. Turning weights back on is a one line change.

We considered a one hot encoding of shrub placements, which would have let us skip the `XY` mixer in favour of a standard `X` mixer on a larger qubit count. The qubit count blowup was large enough that it would only have been interesting on a device with many more qubits than we had on hand.

We considered using the warm start QAOA trick, where the initial state is prepared to bias toward a classical solution. It helped a little on MaxCut but the improvement on wildfire was inside the noise of our small test runs, so we kept the uniform Hamming weight state for clarity.

## What we learned

The two things that mattered most were (a) picking the mixer to fit the constraint so that the optimizer never has to fight the budget penalty, and (b) making the random graph the source of truth for everything downstream. Both changes reduced the amount of state the code has to track and made the failures we did hit much easier to diagnose. Both are visible in the diff that replaced the old `GridQuantumCircuit` wiring with `Grid.BuildQuantumCircuit`.
