"""
Wildfire Resilience - QAOA Layer Comparison (Final)
Runs p=1,2,3 on a 3x3 grid and plots:
  - Grid visualizations per layer + optimal
  - Approximation ratio vs p
  - Runtime vs p
  - Probability distribution of top bitstrings

Expected total runtime: ~45-90 seconds
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from itertools import product
from scipy.optimize import minimize
import time

try:
    from qiskit_aer import AerSimulator
    sim = AerSimulator(method="statevector")
    USE_AER = True
    print(f"✓ Aer {sim}")
except ImportError:
    from qiskit.quantum_info import Statevector
    USE_AER = False
    print("⚠ Falling back to Qiskit statevector")

from qiskit import QuantumCircuit

# ── Parameters ────────────────────────────────────────────────────────────────
GRID_SIZE   = 4
N           = GRID_SIZE ** 2
K           = max(1, round(N * 0.1))
PENALTY     = 50.0
MAX_ITER    = 80
LAYER_RANGE = [1, 2, 3]

# Use top-left 4x4 slice of the realistic 10x10 grid
from wildfire_grid import generate_grid, get_edges as grid_get_edges
FULL_GRID_10 = generate_grid(grid_size=10)
SUBGRID_4x4  = FULL_GRID_10[:4, :4]  # top-left 4x4 patch

print(f"\nGrid: {GRID_SIZE}x{GRID_SIZE} realistic slice | "
      f"Dry Brush: {int(SUBGRID_4x4.sum())} cells | "
      f"K={K} | p={LAYER_RANGE}\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_edges():
    """Edges only between adjacent Dry Brush cells in the 4x4 subgrid."""
    edges = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if SUBGRID_4x4[r, c] != 1:
                continue
            idx = r*GRID_SIZE + c
            if c+1 < GRID_SIZE and SUBGRID_4x4[r, c+1] == 1:
                edges.append((idx, r*GRID_SIZE+c+1))
            if r+1 < GRID_SIZE and SUBGRID_4x4[r+1, c] == 1:
                edges.append((idx, (r+1)*GRID_SIZE+c))
    return edges

EDGES = get_edges()
print(f"Fire edges: {len(EDGES)}")

def classical_cost(bitstring):
    x = np.array([int(b) for b in bitstring])
    fire    = sum((1-x[i])*(1-x[j]) for i, j in EDGES)
    penalty = PENALTY * (x.sum() - K)**2
    return float(fire + penalty)

def build_circuit(gammas, betas, n_layers):
    qc = QuantumCircuit(N)
    qc.h(range(N))
    for layer in range(n_layers):
        g, b = gammas[layer], betas[layer]
        for (i, j) in EDGES:
            qc.rzz(2*g, i, j)
            qc.rz(g, i)
            qc.rz(g, j)
        linear = PENALTY * (N - 2*K)
        for i in range(N):
            qc.rz(linear * g, i)
        for i in range(N):
            qc.rx(2*b, i)
    return qc

def get_probs(qc):
    if USE_AER:
        qc2 = qc.copy()
        qc2.save_statevector()
        sv = np.asarray(sim.run(qc2).result().get_statevector())
        return {
            format(i, f'0{N}b'): abs(a)**2
            for i, a in enumerate(sv) if abs(a)**2 > 1e-9
        }
    sv = Statevector(qc)
    return sv.probabilities_dict()

def best_from_probs(probs):
    best_bs, best_cost = None, float("inf")
    for bs, p in probs.items():
        if p < 1e-6: continue
        c = classical_cost(bs)
        if c < best_cost:
            best_cost, best_bs = c, bs
    return best_bs, best_cost

# ── Brute force ───────────────────────────────────────────────────────────────
print("\nBrute-force baseline...")
t0 = time.time()
bf_cost, bf_bs = float("inf"), None
for bits in product("01", repeat=N):
    bs = "".join(bits)
    c = classical_cost(bs)   # penalty handles K enforcement
    if c < bf_cost:
        bf_cost, bf_bs = c, bs
print(f"Optimal cost: {bf_cost:.2f}  ({time.time()-t0:.2f}s)\n")

# ── QAOA runs ─────────────────────────────────────────────────────────────────
results = {}

for p in LAYER_RANGE:
    print(f"── p={p} ──────────────────────────")
    t0 = time.time()
    np.random.seed(42)
    x0 = np.concatenate([
        np.random.uniform(0.1, 0.5, p),
        np.random.uniform(0.1, 0.5, p)
    ])

    iters = [0]
    def obj(params, _p=p):
        iters[0] += 1
        g, b = params[:_p], params[_p:]
        probs = get_probs(build_circuit(g, b, _p))
        val = sum(prob * classical_cost(bs) for bs, prob in probs.items())
        if iters[0] % 20 == 0:
            print(f"  iter {iters[0]:3d} | <C>={val:.3f} | {time.time()-t0:.1f}s")
        return val

    res = minimize(obj, x0, method="COBYLA",
                   options={"maxiter": MAX_ITER, "rhobeg": 0.5})

    probs = get_probs(build_circuit(res.x[:p], res.x[p:], p))
    best_bs, best_cost = best_from_probs(probs)
    elapsed = time.time() - t0
    ratio = bf_cost / best_cost if best_cost > 0 else 1.0

    results[p] = {
        "cost":         best_cost,
        "exp_val":      res.fun,
        "bitstring":    best_bs,
        "approx_ratio": ratio,
        "time":         elapsed,
        "probs":        probs,
    }
    print(f"  cost={best_cost:.2f} | Toyons={best_bs.count('1')} | "
          f"ratio={ratio:.3f} | {elapsed:.1f}s\n")

# ── Figure ────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 9))
fig.suptitle(
    f"QAOA Wildfire Resilience  —  {GRID_SIZE}×{GRID_SIZE} Grid  (K={K} Toyons, "
    f"Penalty={PENALTY})",
    fontsize=13, fontweight="bold", y=0.99
)

grid_cols = len(LAYER_RANGE) + 1   # +1 for optimal

# ── Row 1: grid plots ─────────────────────────────────────────────────────────
def draw_grid(ax, bs, title):
    vis = SUBGRID_4x4.copy().astype(float)
    sol = np.array([int(b) for b in bs]).reshape(GRID_SIZE, GRID_SIZE)
    vis[sol == 1] = 2
    cmap = mcolors.ListedColormap(["#e8e0d0", "#c8a96e", "#4a7c3f"])
    ax.imshow(vis, cmap=cmap, vmin=0, vmax=2)
    ax.set_title(title, fontsize=9, pad=6)
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.tick_params(length=0, labelsize=7)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if sol[r, c] == 1:
                lbl, col = "T", "white"
            elif SUBGRID_4x4[r, c] == 1:
                lbl, col = "D", "#5a4020"
            else:
                lbl, col = "E", "#999"
            ax.text(c, r, lbl, ha="center", va="center",
                    fontsize=10, fontweight="bold", color=col)

for idx, p in enumerate(LAYER_RANGE):
    ax = fig.add_subplot(2, grid_cols, idx + 1)
    r = results[p]
    draw_grid(ax, r["bitstring"],
              f"p={p}  |  cost={r['cost']:.1f}\n"
              f"ratio={r['approx_ratio']:.3f}  |  {r['time']:.0f}s")

ax_opt = fig.add_subplot(2, grid_cols, grid_cols)
draw_grid(ax_opt, bf_bs, f"Optimal\ncost={bf_cost:.1f}")

from matplotlib.patches import Patch
fig.axes[0].legend(
    handles=[Patch(color="#4a7c3f", label="Toyon"),
             Patch(color="#c8a96e", label="Dry Brush"),
             Patch(color="#e8e0d0", label="Empty")],
    fontsize=8, loc="lower left",
    bbox_to_anchor=(0, -0.2), ncol=3
)

# ── Row 2 left: approximation ratio bar chart ─────────────────────────────────
ax_ratio = fig.add_subplot(2, 3, 4)
ps      = list(results.keys())
ratios  = [results[p]["approx_ratio"] for p in ps]
colors  = ["#378ADD", "#1D9E75", "#D85A30"]

bars = ax_ratio.bar(ps, ratios, color=colors[:len(ps)], width=0.5, zorder=3)
ax_ratio.axhline(1.0, color="#E24B4A", linewidth=1.5,
                 linestyle="--", label="Optimal (ratio=1.0)")
ax_ratio.set_xlabel("QAOA layers (p)", fontsize=10)
ax_ratio.set_ylabel("Approximation ratio", fontsize=10)
ax_ratio.set_title("Quality vs circuit depth", fontsize=10)
ax_ratio.set_xticks(ps)
ax_ratio.set_ylim(0, 1.2)
ax_ratio.legend(fontsize=8)
ax_ratio.grid(axis="y", alpha=0.3, zorder=0)
for bar, ratio in zip(bars, ratios):
    ax_ratio.text(
        bar.get_x() + bar.get_width()/2,
        bar.get_height() + 0.02,
        f"{ratio:.3f}", ha="center", va="bottom", fontsize=10, fontweight="bold"
    )

# ── Row 2 middle: runtime line chart ─────────────────────────────────────────
ax_time = fig.add_subplot(2, 3, 5)
times = [results[p]["time"] for p in ps]
ax_time.plot(ps, times, "o-", color="#7F77DD", linewidth=2, markersize=9)
ax_time.fill_between(ps, times, alpha=0.15, color="#7F77DD")
ax_time.set_xlabel("QAOA layers (p)", fontsize=10)
ax_time.set_ylabel("Runtime (seconds)", fontsize=10)
ax_time.set_title("Runtime vs circuit depth", fontsize=10)
ax_time.set_xticks(ps)
ax_time.grid(alpha=0.3)
for p, t in zip(ps, times):
    ax_time.text(p, t + 0.3, f"{t:.1f}s",
                 ha="center", va="bottom", fontsize=9)

# ── Row 2 right: probability histogram for best-p run ────────────────────────
ax_prob = fig.add_subplot(2, 3, 6)
best_p = max(results, key=lambda p: results[p]["approx_ratio"])
probs  = results[best_p]["probs"]
top    = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:12]

opt_cost = bf_cost * 1.05   # within 5% of optimal = "good"
bar_colors = [
    "#4a7c3f" if classical_cost(bs) <= opt_cost else "#c8a96e"
    for bs, _ in top
]
labels = [bs + f" ({classical_cost(bs):.0f})" for bs, _ in top]
vals   = [v for _, v in top]

ax_prob.barh(range(len(top)), vals, color=bar_colors)
ax_prob.set_yticks(range(len(top)))
ax_prob.set_yticklabels(labels, fontsize=7, family="monospace")
ax_prob.invert_yaxis()
ax_prob.set_xlabel("Probability", fontsize=10)
ax_prob.set_title(
    f"Top bitstrings (p={best_p})\n"
    f"green = cost ≤ {opt_cost:.1f} (near-optimal)",
    fontsize=9
)
ax_prob.grid(axis="x", alpha=0.3)

plt.tight_layout()
out = "./wildfire_layer_comparison.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"Saved → wildfire_layer_comparison.png")
plt.show()
