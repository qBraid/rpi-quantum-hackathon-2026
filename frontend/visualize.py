"""
Visualize QAOA MaxCut results using matplotlib.
Run: python frontend/visualize.py
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# ── Load result files ──────────────────────────────────────────────────────────
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")

DATASETS = {
    "4x4 smoke (sim noise)":  os.path.join(RESULTS_DIR, "hw_smoke",        "summary.json"),
    "4x4 skip-flags":         os.path.join(RESULTS_DIR, "smoke_skipflags", "summary.json"),
    "4x4 test-flags":         os.path.join(RESULTS_DIR, "test_flags",       "summary.json"),
    "6x6 IBM real (run 1)":   os.path.join(RESULTS_DIR, "results",          "hw_ibm_6x6", "summary.json"),
    "6x6 IBM real (run 2)":   os.path.join(RESULTS_DIR, "results",          "summary.json"),
}

data = {}
for label, path in DATASETS.items():
    if os.path.exists(path):
        with open(path) as f:
            data[label] = json.load(f)
    else:
        print(f"[warn] missing: {path}")


# ── Plot 1 — Cost comparison per dataset ──────────────────────────────────────
def plot_cost_comparison(data: dict):
    fig, axes = plt.subplots(1, len(data), figsize=(5 * len(data), 5), sharey=False)
    if len(data) == 1:
        axes = [axes]

    for ax, (label, d) in zip(axes, data.items()):
        names, costs, colors = [], [], []

        greedy = d.get("greedy_cost")
        bf = d.get("brute_force_cost")
        sa = d.get("simulated_annealing_cost")

        if greedy is not None:
            names.append("Greedy"); costs.append(greedy); colors.append("#f59e0b")
        if bf is not None:
            names.append("Brute\nForce"); costs.append(bf); colors.append("#10b981")
        if sa is not None:
            names.append("Sim.\nAnnealing"); costs.append(sa); colors.append("#06b6d4")

        for solver_name, s in d.get("solvers", {}).items():
            fc = s.get("best_feasible_cost")
            if fc is not None:
                names.append(solver_name.replace("_", "\n")); costs.append(fc); colors.append("#8b5cf6")

        hw = d.get("hardware", {})
        if hw.get("best_cost") is not None:
            feasible_tag = " (feasible)" if hw.get("feasible") else " (infeasible)"
            names.append("HW IBM" + feasible_tag.replace(" ", "\n")); costs.append(hw["best_cost"]); colors.append("#ef4444")

        bars = ax.bar(names, costs, color=colors, edgecolor="white", linewidth=0.5)
        ax.bar_label(bars, fmt="%.1f", padding=3, fontsize=8)
        ax.set_title(label, fontsize=9, fontweight="bold")
        ax.set_ylabel("Cut cost (↑ better)")
        ax.set_ylim(0, max(costs) * 1.2 if costs else 1)
        ax.tick_params(axis="x", labelsize=7)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Cut Cost Comparison Across Solvers", fontweight="bold", fontsize=12)
    fig.tight_layout()
    return fig


# ── Plot 2 — Approximation ratios ─────────────────────────────────────────────
def plot_approximation_ratios(data: dict):
    labels, ratios, bar_labels = [], [], []

    for dataset_label, d in data.items():
        for solver_name, s in d.get("solvers", {}).items():
            ar = s.get("approximation_ratio")
            if ar is not None:
                labels.append(f"{dataset_label}\n{solver_name}")
                ratios.append(ar)
                bar_labels.append(f"{ar:.3f}")

    if not ratios:
        return None

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 1.4), 5))
    colors = ["#10b981" if r >= 1.0 else "#ef4444" for r in ratios]
    bars = ax.bar(labels, ratios, color=colors, edgecolor="white", linewidth=0.5)
    ax.bar_label(bars, labels=bar_labels, padding=3, fontsize=8)
    ax.axhline(1.0, color="white", linestyle="--", linewidth=1, label="Optimal (ratio = 1.0)")
    ax.set_title("Approximation Ratio per Solver  (green ≥ 1.0 = beats greedy)", fontweight="bold")
    ax.set_ylabel("Approximation ratio (best_feasible / greedy)")
    ax.set_ylim(0, max(ratios) * 1.2)
    ax.tick_params(axis="x", labelsize=7)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


# ── Plot 3 — Elapsed time ─────────────────────────────────────────────────────
def plot_elapsed_times(data: dict):
    solver_labels, solver_times = [], []
    hw_labels, hw_times = [], []

    for dataset_label, d in data.items():
        for solver_name, s in d.get("solvers", {}).items():
            t = s.get("elapsed")
            if t is not None:
                solver_labels.append(f"{dataset_label}\n{solver_name}")
                solver_times.append(t)

        hw = d.get("hardware", {})
        if hw.get("elapsed") is not None:
            hw_labels.append(dataset_label)
            hw_times.append(hw["elapsed"])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    if solver_times:
        bars = ax1.bar(solver_labels, solver_times, color="#8b5cf6", edgecolor="white", linewidth=0.5)
        ax1.bar_label(bars, fmt="%.3fs", padding=3, fontsize=8)
        ax1.set_title("Classical Solver Elapsed Time", fontweight="bold")
        ax1.set_ylabel("Seconds")
        ax1.tick_params(axis="x", labelsize=7)
        ax1.grid(axis="y", alpha=0.3)
    else:
        ax1.set_visible(False)

    if hw_times:
        bars = ax2.bar(hw_labels, hw_times, color="#ef4444", edgecolor="white", linewidth=0.5)
        ax2.bar_label(bars, fmt="%.2fs", padding=3, fontsize=8)
        ax2.set_title("Hardware Execution Elapsed Time", fontweight="bold")
        ax2.set_ylabel("Seconds")
        ax2.tick_params(axis="x", labelsize=7)
        ax2.grid(axis="y", alpha=0.3)
    else:
        ax2.set_visible(False)

    fig.suptitle("Elapsed Time: Classical Optimization vs Hardware", fontweight="bold", fontsize=12)
    fig.tight_layout()
    return fig


# ── Plot 4 — Hardware circuit stats ───────────────────────────────────────────
def plot_hardware_stats(data: dict):
    hw_entries = [(lbl, d["hardware"]) for lbl, d in data.items()
                  if d.get("hardware") and d["hardware"].get("depth") is not None]
    if not hw_entries:
        return None

    labels = [e[0] for e in hw_entries]
    depths = [e[1]["depth"] for e in hw_entries]
    qubits = [e[1].get("num_qubits", 0) for e in hw_entries]
    shots  = [e[1].get("shots", 0) for e in hw_entries]

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 2.5), 5))
    b1 = ax.bar(x - width, depths, width, label="Circuit Depth", color="#00d4ff", edgecolor="white")
    b2 = ax.bar(x,         qubits, width, label="Qubits Used",   color="#8b5cf6", edgecolor="white")
    b3 = ax.bar(x + width, shots,  width, label="Shots",         color="#f59e0b", edgecolor="white")

    ax.bar_label(b1, padding=3, fontsize=8)
    ax.bar_label(b2, padding=3, fontsize=8)
    ax.bar_label(b3, padding=3, fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("Hardware Circuit Statistics", fontweight="bold")
    ax.set_ylabel("Count")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


# ── Plot 5 — Feasibility summary ──────────────────────────────────────────────
def plot_feasibility(data: dict):
    solver_feasible = solver_infeasible = 0
    hw_feasible     = hw_infeasible     = 0

    for d in data.values():
        for s in d.get("solvers", {}).values():
            if s.get("feasible"):
                solver_feasible += 1
            else:
                solver_infeasible += 1
        hw = d.get("hardware", {})
        if hw:
            if hw.get("feasible"):
                hw_feasible += 1
            elif hw.get("best_cost") is not None:
                hw_infeasible += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 5))

    def pie(ax, yes, no, title):
        if yes + no == 0:
            ax.set_visible(False)
            return
        ax.pie([yes, no], labels=[f"Feasible ({yes})", f"Infeasible ({no})"],
               colors=["#10b981", "#ef4444"], autopct="%1.0f%%",
               startangle=90, textprops={"fontsize": 10})
        ax.set_title(title, fontweight="bold")

    pie(ax1, solver_feasible,  solver_infeasible,  "Classical Solvers — Feasibility")
    pie(ax2, hw_feasible,      hw_infeasible,      "Hardware Runs — Feasibility")

    fig.suptitle("Solution Feasibility (satisfies k-cut partition constraint)",
                 fontweight="bold", fontsize=11)
    fig.tight_layout()
    return fig


# ── Render ─────────────────────────────────────────────────────────────────────
if not data:
    print("No result files found. Run experiments first.")
else:
    plt.style.use("dark_background")

    figs = [
        plot_cost_comparison(data),
        plot_approximation_ratios(data),
        plot_elapsed_times(data),
        plot_hardware_stats(data),
        plot_feasibility(data),
    ]

    for fig in figs:
        if fig is not None:
            fig.patch.set_facecolor("#0d1117")
            for ax in fig.get_axes():
                ax.set_facecolor("#161b22")

    plt.show()
