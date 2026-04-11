"""
Wildfire Resilience - QAOA on ibm_rensselaer (127-qubit Eagle processor)
RPI Quantum Hackathon

Strategy:
  1. Build QAOA circuit for the wildfire cost function
  2. Transpile to Eagle's native gate set (ECR, RZ, SX, X)
  3. Submit via Sampler primitive inside a Session
  4. Compare hardware shot distribution vs classical simulation
  5. Extract best bitstring and visualize on the 10x10 grid

Estimated IBM minutes used:
  - 4x4 test run:  ~2-5 minutes
  - 10x10 full run: ~10-20 minutes
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import time

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler, Session

# ── Connect to ibm_rensselaer ─────────────────────────────────────────────────
print("Connecting to IBM Quantum...")
service = QiskitRuntimeService()
backend = service.backend("ibm_rensselaer")
print(f"✓ Connected: {backend.name}")
print(f"  Qubits: {backend.num_qubits}")
print(f"  Status: {backend.status()}\n")

# ── Realistic grid ────────────────────────────────────────────────────────────
from wildfire_grid import generate_grid
FULL_GRID_10 = generate_grid(grid_size=10)
SUBGRID_4x4  = FULL_GRID_10[:4, :4]

GRID_SIZE   = 4
N           = GRID_SIZE ** 2
K           = max(1, round(N * 0.1))
PENALTY     = 50.0
SHOTS       = 4096
QAOA_LAYERS = 1
GAMMAS_WARMSTART = [0.3]
BETAS_WARMSTART  = [0.4]

print(f"Grid: {GRID_SIZE}x{GRID_SIZE} realistic | "
      f"Dry Brush: {int(SUBGRID_4x4.sum())} | K={K} | "
      f"Layers: {QAOA_LAYERS} | Shots: {SHOTS}\n")

# ── Grid + cost ───────────────────────────────────────────────────────────────
def get_edges():
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

# ── Optimize parameters on Aer before hardware submission ────────────────────
print("\nOptimizing QAOA parameters on Aer...")
from qiskit_aer import AerSimulator as _AerSim
from scipy.optimize import minimize as _minimize

_sim = _AerSim(method="statevector")

def _exp(params):
    qc = QuantumCircuit(N)
    qc.h(range(N))
    g, b = params[0], params[1]
    for (i, j) in EDGES:
        qc.rzz(2*g, i, j); qc.rz(g, i); qc.rz(g, j)
    for i in range(N): qc.rz(PENALTY*(N-2*K)*g, i)
    for i in range(N): qc.rx(2*b, i)
    qc2 = qc.copy(); qc2.save_statevector()
    sv = np.asarray(_sim.run(qc2).result().get_statevector())
    probs = {format(i,f'0{N}b'): abs(a)**2
             for i,a in enumerate(sv) if abs(a)**2 > 1e-9}
    return sum(p*classical_cost(bs) for bs,p in probs.items())

np.random.seed(42)
_res = _minimize(_exp, [0.3, 0.4], method="COBYLA",
                 options={"maxiter": 150, "rhobeg": 0.3})
GAMMAS_WARMSTART = [float(_res.x[0])]
BETAS_WARMSTART  = [float(_res.x[1])]
print(f"Optimized: γ={GAMMAS_WARMSTART[0]:.3f}, β={BETAS_WARMSTART[0]:.3f}\n")

# ── Build QAOA circuit ────────────────────────────────────────────────────────
def build_circuit(gammas, betas):
    qc = QuantumCircuit(N)
    qc.h(range(N))
    for layer in range(QAOA_LAYERS):
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
    qc.measure_all()
    return qc

print("\nBuilding QAOA circuit...")
qc = build_circuit(GAMMAS_WARMSTART, BETAS_WARMSTART)
print(f"Circuit depth (pre-transpile): {qc.depth()}")
print(f"Gate count (pre-transpile):    {qc.size()}")

# ── Transpile to Eagle native gates ───────────────────────────────────────────
print("\nTranspiling for ibm_rensselaer (Eagle, native: ECR/RZ/SX/X)...")
print("This may take 1-2 minutes for larger circuits...")
t0 = time.time()
pm = generate_preset_pass_manager(optimization_level=3, backend=backend)
isa_circuit = pm.run(qc)
print(f"Transpile done in {time.time()-t0:.1f}s")
print(f"Circuit depth (post-transpile): {isa_circuit.depth()}")
print(f"Gate count (post-transpile):    {isa_circuit.size()}")
print(f"2-qubit gates:                  "
      f"{sum(1 for _, qargs, _ in isa_circuit if len(qargs) == 2)}")

# ── Submit to hardware ────────────────────────────────────────────────────────
print(f"\nSubmitting to {backend.name}...")
print("Opening Session (groups jobs to minimize queue wait)...")

with Session(backend=backend) as session:
    sampler = Sampler(mode=session)
    t0 = time.time()
    job = sampler.run([isa_circuit], shots=SHOTS)
    print(f"Job submitted: {job.job_id()}")
    print("Waiting for result (queue + execution time)...")

    result = job.result()
    elapsed = time.time() - t0
    print(f"✓ Result received in {elapsed:.1f}s")

# ── Process results ───────────────────────────────────────────────────────────
# Extract counts from SamplerV2 result
pub_result = result[0]
counts = pub_result.data.meas.get_counts()
total_shots = sum(counts.values())
print(f"\nTotal shots: {total_shots}")
print(f"Unique bitstrings observed: {len(counts)}")

# Find best bitstring — hard filter to exactly K Toyons
best_bs, best_cost = None, float("inf")
valid_count = 0
for bs, count in counts.items():
    bs_corrected = bs[::-1]
    if bs_corrected.count("1") != K:
        continue
    valid_count += 1
    c = classical_cost(bs_corrected)
    if c < best_cost:
        best_cost, best_bs = c, bs_corrected

print(f"Feasible shots (K={K} Toyons): {valid_count} / {total_shots}")

if best_bs is None:
    print(f"⚠ No feasible shots — using most common K-Toyon bitstring")
    # Fallback: find shots with closest to K Toyons
    for bs, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        bs_c = bs[::-1]
        if bs_c.count("1") == K:
            best_bs = bs_c
            best_cost = classical_cost(best_bs)
            break

toyon_count = best_bs.count("1")
# Fire spread: only edges between Dry Brush cells not blocked by Toyon
fire_spread = sum(
    (1-int(best_bs[i]))*(1-int(best_bs[j])) for i,j in EDGES
)
max_spread = len(EDGES)  # max possible = all Dry Brush edges active

print(f"\nBest measured bitstring:")
print(f"  Toyons placed:  {toyon_count} (target {K})")
print(f"  Fire spread:    {fire_spread} / {max_spread}")
print(f"  Total cost:     {best_cost:.1f}")
print(f"  Constraint met: {'✓' if toyon_count == K else '✗'}")

# ── Plot results ──────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    f"QAOA on ibm_rensselaer (127-qubit Eagle)  —  "
    f"{GRID_SIZE}×{GRID_SIZE} Realistic Grid, K={K}, p={QAOA_LAYERS}\n"
    f"{SHOTS} shots  |  Circuit depth: {isa_circuit.depth()}  |  "
    f"{int(SUBGRID_4x4.sum())} Dry Brush cells",
    fontsize=11, fontweight="bold"
)

def draw_grid(ax, bs, title):
    vis = SUBGRID_4x4.copy().astype(float)
    sol = np.array([int(b) for b in bs]).reshape(GRID_SIZE, GRID_SIZE)
    vis[sol == 1] = 2
    cmap = mcolors.ListedColormap(["#e8e0d0", "#c8a96e", "#4a7c3f"])
    ax.imshow(vis, cmap=cmap, vmin=0, vmax=2)
    ax.set_title(title, fontsize=10, pad=8)
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.tick_params(length=0, labelsize=8)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if sol[r, c] == 1:
                lbl, col = "T", "white"
            elif SUBGRID_4x4[r, c] == 1:
                lbl, col = "D", "#5a4020"
            else:
                lbl, col = "E", "#999"
            ax.text(c, r, lbl, ha="center", va="center",
                    fontsize=9, fontweight="bold", color=col)

draw_grid(axes[0], best_bs,
          f"Best solution from hardware\n"
          f"fire spread={fire_spread} | Toyons={toyon_count}")

# Right: top-20 bitstrings by count, colored by cost quality
top_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
labels = [bs[::-1][:8]+"…" for bs, _ in top_counts]
vals   = [v/total_shots for _, v in top_counts]
opt_cost = best_cost * 1.1
bar_colors = [
    "#4a7c3f" if classical_cost(bs[::-1]) <= opt_cost else "#c8a96e"
    for bs, _ in top_counts
]
axes[1].barh(range(len(top_counts)), vals, color=bar_colors)
axes[1].set_yticks(range(len(top_counts)))
axes[1].set_yticklabels(labels, fontsize=7, family="monospace")
axes[1].invert_yaxis()
axes[1].set_xlabel("Probability", fontsize=10)
axes[1].set_title(
    f"Top 20 measured bitstrings\ngreen = near-optimal cost",
    fontsize=10
)
axes[1].grid(axis="x", alpha=0.3)

from matplotlib.patches import Patch
axes[0].legend(
    handles=[Patch(color="#4a7c3f", label="Toyon"),
             Patch(color="#c8a96e", label="Dry Brush"),
             Patch(color="#e8e0d0", label="Empty")],
    loc="lower center", bbox_to_anchor=(1.0, -0.1),
    ncol=3, fontsize=9
)

plt.tight_layout()
out = "./wildfire_hardware_result.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nSaved → wildfire_hardware_result.png")
plt.show()

print("\n── Job summary ──────────────────────────────")
print(f"Job ID:       {job.job_id()}")
print(f"Backend:      {backend.name}")
print(f"Shots:        {SHOTS}")
print(f"Grid:         {GRID_SIZE}x{GRID_SIZE} ({N} qubits)")
print(f"QAOA layers:  {QAOA_LAYERS}")
print(f"Best cost:    {best_cost:.1f}")
print(f"Fire spread:  {fire_spread}")
