# Problem Statement

## The scenario

Picture a square plot of land that has been mapped onto a grid. Some cells of the grid hold dry brush. Fire jumps readily from one brush cell to its neighbour (up, down, left, or right), so a cluster of adjacent brush cells is a running fuse. A fire mitigation crew has a fixed number of Toyon shrubs to plant. Toyon is a low flammability native that breaks the chain when placed into a brush cluster. The crew wants to know where to put the shrubs so that the total amount of brush sitting next to more brush is as small as possible.

The prompt we received describes this as a wildfire mitigation question for a ten by ten grid with a budget of ten shrubs. Our implementation keeps those as defaults but exposes them on the command line so the same code runs on smaller or larger instances for debugging and benchmarking.

## Turning the scenario into math

We assign a binary variable `x_i` to every bush cell on the grid:

```
x_i = 0   the cell still holds dry brush
x_i = 1   the cell has been replaced with a Toyon plant
```

We pair cells that sit next to each other on the grid and call each pair an edge. Two neighbouring brush cells contribute to the hazard exactly when both sides of the edge are still brush, that is when `x_i = 0` and `x_j = 0`. The indicator for that event can be written `(1 - x_i)(1 - x_j)`. Summing over every edge gives the adjacency penalty.

The shrub budget enters as a quadratic penalty. If we are allowed `k` shrubs, we want `sum_i x_i` to land exactly at `k`, so we add `(k - sum_i x_i)^2` to the cost. That term is zero at the feasible budget and grows the further we stray.

Putting the two pieces together, the QUBO we solve is

```
C(x) = sum_{(i, j) in E} (1 - x_i)(1 - x_j) + (k - sum_i x_i)^2
```

The first sum counts brush to brush adjacencies that survive the planting. The second term keeps the solver honest about the budget.

## Why a random graph

The default wildfire implementation builds a rustworkx grid graph where every lattice cell is a node and every north, south, east, west neighbour is an edge. That worked fine, but it did not match the story the problem wanted us to tell: in a real landscape, not every tile is brush. Some tiles are bare ground, rock, or otherwise not part of the fuel. So the natural object is the subgraph induced by brush cells only.

`src/Grid.py` builds exactly that. Given a grid size and a `brush_probability`, it samples which cells hold brush and connects only the brush cells that sit next to each other on the grid. The vertex count of the QAOA circuit then equals the number of bush cells, not the full grid area. This matches the cost function above, where `i` and `j` range over bush nodes, and it means the circuit is smaller for sparser brush layouts.

The refactor that swapped in this random graph lives in [src/problems/wildfire/model.py](../src/problems/wildfire/model.py) and [src/problems/wildfire/problem.py](../src/problems/wildfire/problem.py). Both call a shared helper `build_random_grid` that takes the same seed, so the graph used to build the problem data matches the graph the ansatz is built against. The seed is logged at the start of every run.

## What the cost function really penalizes

The adjacency term is symmetric, so every surviving brush pair contributes a penalty of 1. Two consequences fall out of that.

First, the solver is rewarded for shattering big clusters more than for clipping single stragglers. A line of five brush cells in a row has four surviving edges, so removing the middle cell drops the cost by two, while removing an end cell drops it by only one.

Second, the solver has no opinion about where the brush cluster sits on the map. Cells at the edge of the grid look the same as cells in the middle. We considered adding a risk map that biases the cost toward the hot part of the landscape, and the code still carries a `risk_map` and `edge_weights` structure for that purpose. The current loss uses uniform weights so we can compare cleanly against the QAOA model the hackathon writeup described. The risk map survives as a visualization aid and a hook for later experiments.

## Fire break score

Once the optimizer finishes, we pick the top `k` bush indices by expectation value, treat those as the shrub locations, and compute a `fire_break_score` equal to the total edge weight incident on the chosen set. This is the reward side of the QUBO: how much of the brush to brush adjacency we actually broke. `main.py` prints it for every run and uses it to pick the best result in matrix benchmarks.
