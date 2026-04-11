"""
qBraid Challenge: Compiler-Aware Quantum Benchmarking
RPI Quantum Hackathon 2026

Algorithm: QAOA for Wildfire Resilience Optimization
Source framework: Qiskit
qBraid usage: transpile() with two compilation strategies
Execution environments: Aer simulator + ibm_rensselaer (real hardware)

Research question:
  How well does QAOA for spatial optimization survive compilation
  across frameworks and execution targets?
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler, Session
from qiskit_aer import AerSimulator
from qbraid import transpile as qbraid_transpile
from qbraid.runtime import QbraidProvider
import time

# ── Problem setup ─────────────────────────────────────────────────────────────
# Use top-left 4x4 slice of realistic 10x10 hillside grid
from wildfire_grid import generate_grid
FULL_GRID_10 = generate_grid(grid_size=10)
SUBGRID_4x4  = FULL_GRID_10[:4, :4]

GRID_SIZE   = 4
N           = GRID_SIZE ** 2
K           = max(1, round(N * 0.1))
PENALTY     = 50.0
QAOA_LAYERS = 1
SHOTS       = 4096

print(f"QAOA Wildfire Benchmark — Realistic Grid")
print(f"Grid: {GRID_SIZE}x{GRID_SIZE} | Dry Brush: {int(SUBGRID_4x4.sum())} "
      f"cells | K={K} | p={QAOA_LAYERS} | Shots: {SHOTS}\n")

# ── Grid helpers ──────────────────────────────────────────────────────────────
def get_edges():
    """Edges only between adjacent Dry Brush cells."""
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

# ── Optimize QAOA parameters on Aer ──────────────────────────────────────────
# Ensures ratio=1.0 baseline before hardware comparison
print("Optimizing QAOA parameters on Aer...")
from qiskit_aer import AerSimulator as _AerSim
from scipy.optimize import minimize as _minimize

_sim = _AerSim(method="statevector")

def _exp(params):
    qc = QuantumCircuit(N)
    qc.h(range(N))
    g, b = params[0], params[1]
    for (i, j) in EDGES:
        qc.rzz(2*g, i, j); qc.rz(g, i); qc.rz(g, j)
    linear = PENALTY * (N - 2*K)
    for i in range(N): qc.rz(linear*g, i)
    for i in range(N): qc.rx(2*b, i)
    qc2 = qc.copy(); qc2.save_statevector()
    sv = np.asarray(_sim.run(qc2).result().get_statevector())
    probs = {format(i,f'0{N}b'): abs(a)**2
             for i,a in enumerate(sv) if abs(a)**2 > 1e-9}
    def cost(bs):
        x = np.array([int(c) for c in bs])
        return float(sum((1-x[i])*(1-x[j]) for i,j in EDGES) +
                     PENALTY*(x.sum()-K)**2)
    return sum(p*cost(bs) for bs,p in probs.items())

np.random.seed(42)
_res = _minimize(_exp, [0.3, 0.4], method="COBYLA",
                 options={"maxiter": 150, "rhobeg": 0.3})
GAMMAS = [float(_res.x[0])]
BETAS  = [float(_res.x[1])]
print(f"Optimized params: γ={GAMMAS[0]:.3f}, β={BETAS[0]:.3f}\n")

def classical_cost(bitstring):
    x = np.array([int(b) for b in bitstring])
    fire    = sum((1-x[i])*(1-x[j]) for i, j in EDGES)
    penalty = PENALTY * (x.sum() - K)**2
    return float(fire + penalty)

def fire_spread(bitstring):
    x = np.array([int(b) for b in bitstring])
    return int(sum((1-x[i])*(1-x[j]) for i, j in EDGES))

# ── Build QAOA circuit (Qiskit source representation) ─────────────────────────
def build_qaoa_circuit(gammas, betas, measure=True):
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
    if measure:
        qc.measure_all()
    return qc

print("Building QAOA circuit (Qiskit source representation)...")
source_circuit = build_qaoa_circuit(GAMMAS, BETAS)
print(f"Source circuit depth:      {source_circuit.depth()}")
print(f"Source 2-qubit gate count: {sum(1 for inst in source_circuit.data if len(inst.qubits)==2)}")
print(f"Source circuit width:      {source_circuit.num_qubits} qubits\n")

# ── Connect to IBM ────────────────────────────────────────────────────────────
print("Connecting to ibm_rensselaer...")
service = QiskitRuntimeService()
backend = service.backend("ibm_rensselaer")
print(f"✓ {backend.name} | {backend.num_qubits} qubits\n")

# ── Strategy 1: qBraid default transpilation ──────────────────────────────────
print("=" * 60)
print("Strategy 1: qBraid default transpilation (optimization_level=1)")
print("=" * 60)

t0 = time.time()
# qBraid transpile: convert to qiskit, then use Qiskit pass manager for backend
qiskit_circuit_s1 = qbraid_transpile(source_circuit, "qiskit")
pm_s1 = generate_preset_pass_manager(optimization_level=1, backend=backend)
strategy1_circuit = pm_s1.run(qiskit_circuit_s1)
t_compile_s1 = time.time() - t0

s1_depth     = strategy1_circuit.depth()
s1_2q_gates  = sum(1 for inst in strategy1_circuit.data if len(inst.qubits)==2)
s1_width     = strategy1_circuit.num_qubits
print(f"Compile time:   {t_compile_s1:.2f}s")
print(f"Circuit depth:  {s1_depth}")
print(f"2-qubit gates:  {s1_2q_gates}")
print(f"Circuit width:  {s1_width} qubits\n")

# ── Strategy 2: qBraid aggressive optimization ────────────────────────────────
print("=" * 60)
print("Strategy 2: qBraid aggressive transpilation (optimization_level=3)")
print("=" * 60)

t0 = time.time()
# Same qBraid conversion, different Qiskit optimization level
qiskit_circuit_s2 = qbraid_transpile(source_circuit, "qiskit")
pm_s2 = generate_preset_pass_manager(optimization_level=3, backend=backend)
strategy2_circuit = pm_s2.run(qiskit_circuit_s2)
t_compile_s2 = time.time() - t0

s2_depth    = strategy2_circuit.depth()
s2_2q_gates = sum(1 for inst in strategy2_circuit.data if len(inst.qubits)==2)
s2_width    = strategy2_circuit.num_qubits
print(f"Compile time:   {t_compile_s2:.2f}s")
print(f"Circuit depth:  {s2_depth}")
print(f"2-qubit gates:  {s2_2q_gates}")
print(f"Circuit width:  {s2_width} qubits\n")

depth_reduction = 100*(s1_depth - s2_depth)/s1_depth
gate_reduction  = 100*(s1_2q_gates - s2_2q_gates)/s1_2q_gates
print(f"Depth reduction:     {depth_reduction:.1f}%")
print(f"2Q gate reduction:   {gate_reduction:.1f}%\n")

# ── Execute on Aer (Environment 1) ────────────────────────────────────────────
print("=" * 60)
print("Environment 1: Aer statevector simulator (ideal)")
print("=" * 60)

aer_sim = AerSimulator(method="statevector")

def run_aer(circuit, label):
    t0 = time.time()
    counts = aer_sim.run(circuit, shots=SHOTS).result().get_counts()
    elapsed = time.time() - t0
    best_bs, best_cost = None, float("inf")
    for bs, _ in counts.items():
        c = classical_cost(bs[::-1])
        if c < best_cost:
            best_cost, best_bs = c, bs[::-1]
    fs = fire_spread(best_bs)
    toyon_count = best_bs.count("1")
    print(f"  [{label}] fire spread={fs} | Toyons={toyon_count} | "
          f"best cost={best_cost:.1f} | time={elapsed:.2f}s")
    return {"fire_spread": fs, "cost": best_cost,
            "toyons": toyon_count, "counts": counts,
            "bitstring": best_bs, "time": elapsed}

print("Running Strategy 1 on Aer...")
aer_s1 = run_aer(strategy1_circuit, "S1 default")
print("Running Strategy 2 on Aer...")
aer_s2 = run_aer(strategy2_circuit, "S2 aggressive")

# ── Execute on ibm_rensselaer (Environment 2) ─────────────────────────────────
print("\n" + "=" * 60)
print("Environment 2: ibm_rensselaer (127-qubit Eagle, real hardware)")
print("=" * 60)

hw_s1, hw_s2 = None, None
print("Opening Session on ibm_rensselaer...")
with Session(backend=backend) as session:
    sampler = Sampler(mode=session)

    print("Submitting Strategy 1...")
    t0 = time.time()
    job1 = sampler.run([strategy1_circuit], shots=SHOTS)
    print(f"  Job ID: {job1.job_id()}")
    result1 = job1.result()
    counts1 = result1[0].data.meas.get_counts()
    t_hw_s1 = time.time() - t0

    best_bs, best_cost = None, float("inf")
    for bs, _ in counts1.items():
        c = classical_cost(bs[::-1])
        if c < best_cost:
            best_cost, best_bs = c, bs[::-1]
    hw_s1 = {"fire_spread": fire_spread(best_bs), "cost": best_cost,
              "toyons": best_bs.count("1"), "counts": counts1,
              "bitstring": best_bs, "time": t_hw_s1}
    print(f"  [S1 hardware] fire spread={hw_s1['fire_spread']} | "
          f"Toyons={hw_s1['toyons']} | time={t_hw_s1:.1f}s")

    print("Submitting Strategy 2...")
    t0 = time.time()
    job2 = sampler.run([strategy2_circuit], shots=SHOTS)
    print(f"  Job ID: {job2.job_id()}")
    result2 = job2.result()
    counts2 = result2[0].data.meas.get_counts()
    t_hw_s2 = time.time() - t0

    best_bs, best_cost = None, float("inf")
    for bs, _ in counts2.items():
        c = classical_cost(bs[::-1])
        if c < best_cost:
            best_cost, best_bs = c, bs[::-1]
    hw_s2 = {"fire_spread": fire_spread(best_bs), "cost": best_cost,
              "toyons": best_bs.count("1"), "counts": counts2,
              "bitstring": best_bs, "time": t_hw_s2}
    print(f"  [S2 hardware] fire spread={hw_s2['fire_spread']} | "
          f"Toyons={hw_s2['toyons']} | time={t_hw_s2:.1f}s")

# ── Brute force optimal ───────────────────────────────────────────────────────
from itertools import product as iproduct
print("\nComputing brute-force optimal...")
bf_cost, bf_bs = float("inf"), None
for bits in iproduct("01", repeat=N):
    bs = "".join(bits)
    c = classical_cost(bs)
    if c < bf_cost:
        bf_cost, bf_bs = c, bs
bf_fire = fire_spread(bf_bs)
print(f"Optimal fire spread: {bf_fire} | cost: {bf_cost:.1f}")

def approx_ratio(result_fire):
    return bf_fire / result_fire if result_fire > 0 else 1.0

# ── Summary table ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print(f"{'Metric':<30} {'S1 Aer':>10} {'S2 Aer':>10} "
      f"{'S1 HW':>10} {'S2 HW':>10}")
print("-" * 60)
print(f"{'Circuit depth':<30} {s1_depth:>10} {s2_depth:>10} "
      f"{'—':>10} {'—':>10}")
print(f"{'2-qubit gates':<30} {s1_2q_gates:>10} {s2_2q_gates:>10} "
      f"{'—':>10} {'—':>10}")
print(f"{'Fire spread':<30} {aer_s1['fire_spread']:>10} "
      f"{aer_s2['fire_spread']:>10} "
      f"{hw_s1['fire_spread']:>10} {hw_s2['fire_spread']:>10}")
print(f"{'Approximation ratio':<30} "
      f"{approx_ratio(aer_s1['fire_spread']):>10.3f} "
      f"{approx_ratio(aer_s2['fire_spread']):>10.3f} "
      f"{approx_ratio(hw_s1['fire_spread']):>10.3f} "
      f"{approx_ratio(hw_s2['fire_spread']):>10.3f}")
print(f"{'Toyons placed (target={K})':<30} "
      f"{aer_s1['toyons']:>10} {aer_s2['toyons']:>10} "
      f"{hw_s1['toyons']:>10} {hw_s2['toyons']:>10}")
print(f"{'Execution time (s)':<30} "
      f"{aer_s1['time']:>10.1f} {aer_s2['time']:>10.1f} "
      f"{hw_s1['time']:>10.1f} {hw_s2['time']:>10.1f}")

# ── Visualization ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
fig.suptitle(
    "qBraid Compiler-Aware Benchmarking: QAOA Wildfire Optimization\n"
    f"{GRID_SIZE}×{GRID_SIZE} Grid | K={K} Toyons | p={QAOA_LAYERS} | "
    f"{SHOTS} shots | ibm_rensselaer (127-qubit Eagle)",
    fontsize=12, fontweight="bold"
)
gs = gridspec.GridSpec(2, 4, figure=fig, hspace=0.45, wspace=0.35)

import matplotlib.colors as mcolors

def draw_grid(ax, bitstring, title):
    vis = SUBGRID_4x4.copy().astype(float)
    sol = np.array([int(b) for b in bitstring]).reshape(GRID_SIZE, GRID_SIZE)
    vis[sol == 1] = 2
    cmap = mcolors.ListedColormap(["#e8e0d0", "#c8a96e", "#4a7c3f"])
    ax.imshow(vis, cmap=cmap, vmin=0, vmax=2)
    ax.set_title(title, fontsize=8, pad=5)
    ax.set_xticks(range(GRID_SIZE)); ax.set_yticks(range(GRID_SIZE))
    ax.tick_params(length=0, labelsize=6)
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if sol[r, c] == 1:
                lbl, col = "T", "white"
            elif vis[r, c] == 1:
                lbl, col = "D", "#5a4020"
            else:
                lbl, col = "E", "#888"
            ax.text(c, r, lbl, ha="center", va="center",
                    fontsize=7, fontweight="bold", color=col)

ax1 = fig.add_subplot(gs[0, 0])
draw_grid(ax1, aer_s1["bitstring"],
          f"S1 · Aer\nfire={aer_s1['fire_spread']} "
          f"ratio={approx_ratio(aer_s1['fire_spread']):.3f}")

ax2 = fig.add_subplot(gs[0, 1])
draw_grid(ax2, aer_s2["bitstring"],
          f"S2 · Aer\nfire={aer_s2['fire_spread']} "
          f"ratio={approx_ratio(aer_s2['fire_spread']):.3f}")

ax3 = fig.add_subplot(gs[0, 2])
draw_grid(ax3, hw_s1["bitstring"],
          f"S1 · ibm_rensselaer\nfire={hw_s1['fire_spread']} "
          f"ratio={approx_ratio(hw_s1['fire_spread']):.3f}")

ax4 = fig.add_subplot(gs[0, 3])
draw_grid(ax4, hw_s2["bitstring"],
          f"S2 · ibm_rensselaer\nfire={hw_s2['fire_spread']} "
          f"ratio={approx_ratio(hw_s2['fire_spread']):.3f}")

from matplotlib.patches import Patch
ax1.legend(
    handles=[Patch(color="#4a7c3f", label="Toyon"),
             Patch(color="#c8a96e", label="Dry Brush")],
    fontsize=7, loc="lower left",
    bbox_to_anchor=(0, -0.22), ncol=2
)

# Resource cost comparison
ax5 = fig.add_subplot(gs[1, 0:2])
x = np.arange(2)
w = 0.35
bars1 = ax5.bar(x - w/2, [s1_depth, s1_2q_gates], w,
                label="S1: default (opt=1)", color="#378ADD")
bars2 = ax5.bar(x + w/2, [s2_depth, s2_2q_gates], w,
                label="S2: aggressive (opt=3)", color="#1D9E75")
ax5.set_xticks(x)
ax5.set_xticklabels(["Circuit depth", "2-qubit gates"])
ax5.set_title("Compiled resource cost", fontsize=10)
ax5.legend(fontsize=8)
ax5.grid(axis="y", alpha=0.3)
for bar in list(bars1) + list(bars2):
    ax5.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 1,
             str(int(bar.get_height())),
             ha="center", va="bottom", fontsize=8)

# Quality comparison
ax6 = fig.add_subplot(gs[1, 2:4])
envs   = ["Aer sim\n(ideal)", "ibm_rensselaer\n(hardware)"]
s1_ratios = [approx_ratio(aer_s1["fire_spread"]),
             approx_ratio(hw_s1["fire_spread"])]
s2_ratios = [approx_ratio(aer_s2["fire_spread"]),
             approx_ratio(hw_s2["fire_spread"])]
x = np.arange(2)
ax6.bar(x - w/2, s1_ratios, w, label="S1: default", color="#378ADD")
ax6.bar(x + w/2, s2_ratios, w, label="S2: aggressive", color="#1D9E75")
ax6.axhline(1.0, color="#E24B4A", linewidth=1.5,
            linestyle="--", label="Optimal (ratio=1.0)")
ax6.set_xticks(x)
ax6.set_xticklabels(envs)
ax6.set_ylim(0, 1.2)
ax6.set_title("Output quality (approximation ratio)", fontsize=10)
ax6.legend(fontsize=8)
ax6.grid(axis="y", alpha=0.3)
for i, (r1, r2) in enumerate(zip(s1_ratios, s2_ratios)):
    ax6.text(i - w/2, r1 + 0.02, f"{r1:.3f}",
             ha="center", va="bottom", fontsize=8)
    ax6.text(i + w/2, r2 + 0.02, f"{r2:.3f}",
             ha="center", va="bottom", fontsize=8)

plt.savefig("./qbraid_benchmark_results.png",
            dpi=150, bbox_inches="tight")
print("\nSaved → qbraid_benchmark_results.png")
plt.show()

# ── Noise analysis: TVD and Hellinger distance ────────────────────────────────
print("\n" + "=" * 60)
print("Noise analysis: TVD and Hellinger distance")
print("=" * 60)

def get_distribution(counts, n_qubits):
    """Convert counts dict to full probability distribution over 2^n states."""
    total = sum(counts.values())
    dist = np.zeros(2**n_qubits)
    for bs, count in counts.items():
        idx = int(bs[::-1], 2)  # correct for Qiskit bit ordering
        dist[idx] = count / total
    return dist

def tvd(p, q):
    """Total Variation Distance: 0 = identical, 1 = completely different."""
    return 0.5 * np.sum(np.abs(p - q))

def hellinger(p, q):
    """Hellinger distance: 0 = identical, 1 = completely different."""
    return np.sqrt(1 - np.sum(np.sqrt(p * q)))

# Get Aer distributions as the "ideal" reference
aer_dist_s1 = get_distribution(aer_s1["counts"], N)
aer_dist_s2 = get_distribution(aer_s2["counts"], N)
hw_dist_s1  = get_distribution(hw_s1["counts"],  N)
hw_dist_s2  = get_distribution(hw_s2["counts"],  N)

tvd_s1  = tvd(aer_dist_s1,  hw_dist_s1)
tvd_s2  = tvd(aer_dist_s2,  hw_dist_s2)
hell_s1 = hellinger(aer_dist_s1, hw_dist_s1)
hell_s2 = hellinger(aer_dist_s2, hw_dist_s2)

print(f"{'Metric':<35} {'S1 (depth=232)':>16} {'S2 (depth=217)':>16}")
print("-" * 68)
print(f"{'TVD (ideal vs hardware)':<35} {tvd_s1:>16.4f} {tvd_s2:>16.4f}")
print(f"{'Hellinger (ideal vs hardware)':<35} {hell_s1:>16.4f} {hell_s2:>16.4f}")
print(f"{'Approx ratio (hardware)':<35} "
      f"{approx_ratio(hw_s1['fire_spread']):>16.3f} "
      f"{approx_ratio(hw_s2['fire_spread']):>16.3f}")
print()
if tvd_s1 < tvd_s2:
    print(f"S1 has lower TVD ({tvd_s1:.4f} vs {tvd_s2:.4f}) — "
          f"hardware distribution closer to ideal")
else:
    print(f"S2 has lower TVD ({tvd_s2:.4f} vs {tvd_s1:.4f}) — "
          f"hardware distribution closer to ideal")

# ── Add noise panel to figure ─────────────────────────────────────────────────
# (extend the existing figure with a third row)
fig2, axes2 = plt.subplots(1, 3, figsize=(16, 4))
fig2.suptitle("Noise Analysis: Ideal vs Hardware Shot Distributions",
              fontsize=11, fontweight="bold")

def plot_distribution_comparison(ax, ideal_counts, hw_counts, title, n):
    """Plot top-20 bitstrings comparing ideal vs hardware probability."""
    total_ideal = sum(ideal_counts.values())
    total_hw    = sum(hw_counts.values())
    # Get union of top bitstrings
    all_bs = set(list(ideal_counts.keys())[:20]) | set(list(hw_counts.keys())[:20])
    top = sorted(all_bs,
                 key=lambda b: ideal_counts.get(b, 0)/total_ideal,
                 reverse=True)[:15]
    ideal_probs = [ideal_counts.get(b, 0)/total_ideal for b in top]
    hw_probs    = [hw_counts.get(b, 0)/total_hw for b in top]
    x = np.arange(len(top))
    w = 0.4
    ax.bar(x - w/2, ideal_probs, w, label="Aer (ideal)", color="#378ADD", alpha=0.8)
    ax.bar(x + w/2, hw_probs,    w, label="Hardware",    color="#E24B4A", alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([b[::-1][:6] for b in top],
                       rotation=45, ha="right", fontsize=7,
                       fontfamily="monospace")
    ax.set_title(title, fontsize=9)
    ax.set_ylabel("Probability", fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)

plot_distribution_comparison(
    axes2[0], aer_s1["counts"], hw_s1["counts"],
    f"Strategy 1 (opt=1)\nTVD={tvd_s1:.4f}  Hellinger={hell_s1:.4f}", N
)
plot_distribution_comparison(
    axes2[1], aer_s2["counts"], hw_s2["counts"],
    f"Strategy 2 (opt=3)\nTVD={tvd_s2:.4f}  Hellinger={hell_s2:.4f}", N
)

# TVD / Hellinger bar comparison
ax3 = axes2[2]
metrics = ["TVD", "Hellinger"]
s1_vals = [tvd_s1, hell_s1]
s2_vals = [tvd_s2, hell_s2]
x = np.arange(2)
w = 0.35
bars1 = ax3.bar(x - w/2, s1_vals, w, label="S1: default (opt=1)",
                color="#378ADD")
bars2 = ax3.bar(x + w/2, s2_vals, w, label="S2: aggressive (opt=3)",
                color="#1D9E75")
ax3.set_xticks(x)
ax3.set_xticklabels(metrics)
ax3.set_title("Noise impact summary\n(lower = hardware closer to ideal)",
              fontsize=9)
ax3.legend(fontsize=8)
ax3.grid(axis="y", alpha=0.3)
for bar in list(bars1) + list(bars2):
    ax3.text(bar.get_x() + bar.get_width()/2,
             bar.get_height() + 0.002,
             f"{bar.get_height():.4f}",
             ha="center", va="bottom", fontsize=8)

plt.tight_layout()
out2 = "./qbraid_noise_analysis.png"
plt.savefig(out2, dpi=150, bbox_inches="tight")
print(f"\nSaved → qbraid_noise_analysis.png")
plt.show()
print("1. Algorithm: QAOA for wildfire Toyon placement optimization")
print("2. Source representation: Qiskit QuantumCircuit")
print("3. qBraid transformation: qbraid.transpile() to Eagle ISA")
print(f"4. Strategies compared: opt_level=1 vs opt_level=3")
print(f"5. Changes: depth {s1_depth}→{s2_depth} "
      f"({depth_reduction:.1f}% reduction), "
      f"2Q gates {s1_2q_gates}→{s2_2q_gates} "
      f"({gate_reduction:.1f}% reduction)")
best_sim = "S2" if aer_s2["fire_spread"] <= aer_s1["fire_spread"] else "S1"
print(f"6. Best strategy on simulator: {best_sim}")
best_hw  = "S2" if hw_s2["fire_spread"] <= hw_s1["fire_spread"] else "S1"
print(f"   Best strategy on hardware:  {best_hw}")
print(f"7. Cost of best strategy: depth={s2_depth}, 2Q gates={s2_2q_gates}")
