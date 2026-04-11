"""
Wildfire Resilience - Problem-Level Decomposition QAOA
Realistic hillside grid: 65% Dry Brush, 35% Empty (fixed seed=42)

Key improvement over uniform grid:
  - Empty cells create irregular topology with genuine optimization structure
  - Fire edges only exist between adjacent Dry Brush cells
  - Optimal Toyon placement is non-trivial and non-uniform
  - Greedy heuristic no longer trivially finds checkerboard patterns

Subgrid layout (4 x 5x5):
  ┌─────┬─────┐
  │  A  │  B  │
  ├─────┼─────┤
  │  C  │  D  │
  └─────┴─────┘
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy.optimize import minimize
import time

from wildfire_grid import (
    GRID, FULL_GRID, K_GLOBAL, MAX_SPREAD,
    DRY_BRUSH_COUNT, subgrid_info, fire_spread_count,
    greedy_marginal
)

# ── Try hardware, fall back to Aer ───────────────────────────────────────────
USE_HARDWARE = False   # ← set True to run on ibm_rensselaer

if USE_HARDWARE:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit_ibm_runtime import Session
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    service = QiskitRuntimeService()
    backend = service.backend("ibm_rensselaer")
    print(f"✓ Connected to {backend.name} ({backend.num_qubits} qubits)")
else:
    print("✓ Using Aer MPS simulator (RAM-efficient)")

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

# ── Parameters ────────────────────────────────────────────────────────────────
SUB_GRID       = 5
N_SUB          = SUB_GRID ** 2
# K_SUB is now computed per-subgrid proportionally to Dry Brush count
PENALTY        = 200.0
BOUNDARY_ALPHA = 0.5
QAOA_LAYERS    = 1
SHOTS          = 4096
MAX_ITER       = 60

SUBGRIDS = {
    "A": (0, 0), "B": (0, 5),
    "C": (5, 0), "D": (5, 5),
}

print(f"\nGrid: {FULL_GRID}x{FULL_GRID} | Dry Brush: {DRY_BRUSH_COUNT} cells "
      f"({100*DRY_BRUSH_COUNT/FULL_GRID**2:.0f}%) | "
      f"Max fire spread: {MAX_SPREAD}")
print(f"Subgrid: {SUB_GRID}x{SUB_GRID} | K_sub=proportional | "
      f"p={QAOA_LAYERS} | Penalty={PENALTY}\n")

# ── QAOA circuit ──────────────────────────────────────────────────────────────
def build_circuit(gammas, betas, edges, n, k, penalty,
                  boundary_indices=None, boundary_alpha=0.0, measure=True):
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for layer in range(QAOA_LAYERS):
        g, b = gammas[layer], betas[layer]
        for (i, j) in edges:
            qc.rzz(2*g, i, j)
            qc.rz(g, i)
            qc.rz(g, j)
        linear = penalty * (n - 2*k)
        for i in range(n):
            qc.rz(linear * g, i)
        if boundary_indices and boundary_alpha > 0:
            for i in boundary_indices:
                qc.rz(boundary_alpha * g, i)
        for i in range(n):
            qc.rx(2*b, i)
    if measure:
        qc.measure_all()
    return qc

def classical_cost_sub(bitstring, edges, k, penalty,
                        boundary_indices=None, boundary_alpha=0.0):
    x = np.array([int(b) for b in bitstring])
    fire = sum((1-x[i])*(1-x[j]) for i,j in edges)
    pen  = penalty * (x.sum() - k)**2
    bpen = boundary_alpha * sum(1-x[i] for i in (boundary_indices or []))
    return float(fire + pen + bpen)

# ── Run QAOA on one subgrid ───────────────────────────────────────────────────
def run_subgrid_qaoa(name, row_start, col_start, session=None):
    cells, edges, b_idxs = subgrid_info(
        GRID, row_start, col_start, SUB_GRID, FULL_GRID)
    b_alpha = BOUNDARY_ALPHA
    n_dry = sum(1 for gi in cells
                if GRID[gi // FULL_GRID, gi % FULL_GRID] == 1)

    # Proportional K budget: allocate Toyons based on this subgrid's
    # share of total Dry Brush cells across the full grid
    k_sub = max(1, round(n_dry * (K_GLOBAL / DRY_BRUSH_COUNT)))

    print(f"\n── Subgrid {name} "
          f"(rows {row_start}-{row_start+SUB_GRID-1}, "
          f"cols {col_start}-{col_start+SUB_GRID-1}) ──")
    print(f"   Cells: {len(cells)} | Dry Brush: {n_dry} | "
          f"Fire edges: {len(edges)} | Boundary: {len(b_idxs)} | "
          f"k_sub={k_sub}")

    mps_sim = AerSimulator(method="matrix_product_state")

    def expectation(params):
        g, b = params[:QAOA_LAYERS], params[QAOA_LAYERS:]
        qc = build_circuit(g, b, edges, N_SUB, k_sub, PENALTY,
                           b_idxs, b_alpha, measure=True)
        counts = mps_sim.run(qc, shots=2048).result().get_counts()
        total = sum(counts.values())
        return sum(
            (c / total) * classical_cost_sub(
                bs[::-1], edges, k_sub, PENALTY, b_idxs, b_alpha)
            for bs, c in counts.items()
        )

    np.random.seed(42)
    x0 = np.concatenate([
        np.random.uniform(0.1, 0.5, QAOA_LAYERS),
        np.random.uniform(0.1, 0.5, QAOA_LAYERS)
    ])
    t0 = time.time()
    result = minimize(expectation, x0, method="COBYLA",
                      options={"maxiter": MAX_ITER, "rhobeg": 0.5})
    gammas = result.x[:QAOA_LAYERS]
    betas  = result.x[QAOA_LAYERS:]
    print(f"   Params: gamma={gammas.round(3)}, beta={betas.round(3)} "
          f"({time.time()-t0:.1f}s)")

    qc_final = build_circuit(gammas, betas, edges, N_SUB, k_sub, PENALTY,
                              b_idxs, b_alpha)

    if USE_HARDWARE:
        print(f"   Transpiling for Eagle...")
        pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
        isa_qc = pm.run(qc_final)
        print(f"   Depth: {isa_qc.depth()} | Gates: {isa_qc.size()}")
        sampler = Sampler(mode=session)
        job = sampler.run([isa_qc], shots=SHOTS)
        print(f"   Job: {job.job_id()}")
        counts = job.result()[0].data.meas.get_counts()
    else:
        counts = mps_sim.run(qc_final, shots=SHOTS).result().get_counts()

    # Hard k_sub filter
    best_bs, best_cost = None, float("inf")
    valid = 0
    for bs, cnt in counts.items():
        bs_c = bs[::-1]
        if bs_c.count("1") != k_sub:
            continue
        valid += 1
        c = classical_cost_sub(bs_c, edges, k_sub, PENALTY, b_idxs, b_alpha)
        if c < best_cost:
            best_cost, best_bs = c, bs_c

    if best_bs is None:
        print(f"   Warning: No feasible shots — greedy fallback")
        local_degrees = {}
        for li in range(N_SUB):
            local_degrees[li] = sum(1 for (a, b) in edges if a == li or b == li)
        top = sorted(local_degrees, key=local_degrees.get, reverse=True)[:k_sub]
        best_bs = "".join("1" if i in top else "0" for i in range(N_SUB))
        best_cost = classical_cost_sub(best_bs, edges, k_sub, PENALTY,
                                        b_idxs, b_alpha)
    else:
        print(f"   Feasible shots: {valid} / {len(counts)}")

    local_fire = sum(
        (1-int(best_bs[i]))*(1-int(best_bs[j])) for i,j in edges)
    print(f"   Best: cost={best_cost:.1f} | "
          f"Toyons={best_bs.count('1')} (k_sub={k_sub}) | "
          f"local fire={local_fire}")

    return {
        "name": name, "cells": cells, "edges": edges,
        "bitstring": best_bs, "cost": best_cost,
        "fire": local_fire, "toyons": best_bs.count("1"),
        "k_sub": k_sub, "n_dry": n_dry,
        "counts": counts, "params": result.x,
    }

# ── Run all subgrids ──────────────────────────────────────────────────────────
print("Starting subgrid decomposition...")
subresults = {}

if USE_HARDWARE:
    with Session(backend=backend) as session:
        for name, (r0, c0) in SUBGRIDS.items():
            subresults[name] = run_subgrid_qaoa(name, r0, c0, session)
else:
    for name, (r0, c0) in SUBGRIDS.items():
        subresults[name] = run_subgrid_qaoa(name, r0, c0)

# ── Combine solutions ─────────────────────────────────────────────────────────
print("\n── Combining solutions ──────────────────────────────────────")
full_solution = np.zeros(FULL_GRID**2, dtype=int)
for name, res in subresults.items():
    for local_i, global_i in enumerate(res["cells"]):
        if res["bitstring"][local_i] == "1":
            full_solution[global_i] = 1

total = int(full_solution.sum())
print(f"Toyons before trimming: {total} (target: {K_GLOBAL})")

if total > K_GLOBAL:
    for _ in range(total - K_GLOBAL):
        toyon_idxs = np.where(full_solution == 1)[0]
        before = fire_spread_count(full_solution, GRID, FULL_GRID)
        costs = {}
        for idx in toyon_idxs:
            full_solution[idx] = 0
            costs[idx] = fire_spread_count(full_solution, GRID, FULL_GRID) - before
            full_solution[idx] = 1
        least = min(costs, key=costs.get)
        full_solution[least] = 0
        print(f"  Removed cell {least} (fire penalty: {costs[least]})")

elif total < K_GLOBAL:
    for _ in range(K_GLOBAL - total):
        empty_idxs = np.where(full_solution == 0)[0]
        before = fire_spread_count(full_solution, GRID, FULL_GRID)
        costs = {}
        for idx in empty_idxs:
            full_solution[idx] = 1
            costs[idx] = before - fire_spread_count(full_solution, GRID, FULL_GRID)
            full_solution[idx] = 0
        best = max(costs, key=costs.get)
        full_solution[best] = 1
        print(f"  Added cell {best} (fire reduction: {costs[best]})")

fire = fire_spread_count(full_solution, GRID, FULL_GRID)
print(f"\nFinal Toyons: {int(full_solution.sum())}")
print(f"Fire spread:  {fire} / {MAX_SPREAD}")

# ── Greedy baseline ───────────────────────────────────────────────────────────
print("\nGreedy baseline (marginal gain)...")
greedy = greedy_marginal(GRID, K_GLOBAL, FULL_GRID)
greedy_fire = fire_spread_count(greedy, GRID, FULL_GRID)
diff = greedy_fire - fire
print(f"Greedy: {greedy_fire} | QAOA: {fire} | "
      f"Diff: {diff:+d} ({'QAOA wins' if diff>0 else 'Greedy wins' if diff<0 else 'Tie'})")

# ── Visualize ─────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
method = "ibm_rensselaer" if USE_HARDWARE else "Aer simulation"
fig.suptitle(
    f"Wildfire Resilience — {FULL_GRID}x{FULL_GRID} Realistic Grid "
    f"({DRY_BRUSH_COUNT} Dry Brush, {FULL_GRID**2-DRY_BRUSH_COUNT} Empty)\n"
    f"4x{SUB_GRID}x{SUB_GRID} QAOA  |  {method}  |  K={K_GLOBAL} Toyons",
    fontsize=11, fontweight="bold"
)

def draw(ax, solution, title):
    vis = GRID.reshape(FULL_GRID, FULL_GRID).copy().astype(float)
    sol = solution.reshape(FULL_GRID, FULL_GRID)
    vis[sol == 1] = 2
    cmap = mcolors.ListedColormap(["#e8e0d0", "#c8a96e", "#4a7c3f"])
    ax.imshow(vis, cmap=cmap, vmin=0, vmax=2)
    ax.set_title(title, fontsize=10, pad=8)
    ax.set_xticks(range(FULL_GRID))
    ax.set_yticks(range(FULL_GRID))
    ax.tick_params(length=0, labelsize=7)
    for r in range(FULL_GRID):
        for c in range(FULL_GRID):
            if sol[r, c] == 1:
                ax.plot(c, r, 'w.', markersize=10)
    for line in [4.5]:
        ax.axhline(line, color='white', linewidth=1.2,
                   linestyle='--', alpha=0.4)
        ax.axvline(line, color='white', linewidth=1.2,
                   linestyle='--', alpha=0.4)
    for label, (r0, c0) in [("A",(1,1)),("B",(1,6)),
                              ("C",(6,1)),("D",(6,6))]:
        ax.text(c0+1, r0+1, label, color='white',
                fontsize=14, fontweight='bold', alpha=0.35)

draw(axes[0], full_solution,
     f"Decomposition QAOA\nfire={fire}/{MAX_SPREAD} | "
     f"Toyons={int(full_solution.sum())}")
draw(axes[1], greedy,
     f"Greedy (marginal gain)\nfire={greedy_fire}/{MAX_SPREAD} | "
     f"Toyons={int(greedy.sum())}")

from matplotlib.patches import Patch
axes[0].legend(
    handles=[Patch(color="#4a7c3f", label="Toyon"),
             Patch(color="#c8a96e", label="Dry Brush"),
             Patch(color="#e8e0d0", label="Empty")],
    loc="lower center", bbox_to_anchor=(1.0, -0.08),
    ncol=3, fontsize=9
)
plt.tight_layout()
plt.savefig("./wildfire_decomposed_10x10.png", dpi=150, bbox_inches="tight")
print("Saved -> wildfire_decomposed_10x10.png")
plt.show()

print("\n── Summary ──────────────────────────────────────────────────")
print(f"Method:   Subgrid decomposition QAOA ({method})")
print(f"Grid:     {FULL_GRID}x{FULL_GRID} | {DRY_BRUSH_COUNT} Dry Brush | "
      f"{FULL_GRID**2-DRY_BRUSH_COUNT} Empty")
print(f"Toyons:   {int(full_solution.sum())} / {K_GLOBAL}")
print(f"QAOA:     {fire} / {MAX_SPREAD}")
print(f"Greedy:   {greedy_fire} / {MAX_SPREAD}")
for name, res in subresults.items():
    print(f"  {name}: k_sub={res['k_sub']} | n_dry={res['n_dry']} | "
          f"cost={res['cost']:.1f} | Toyons={res['toyons']} | "
          f"fire={res['fire']}")
