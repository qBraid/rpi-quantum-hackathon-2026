"""
qBraid Challenge — Compiler-Aware Quantum Benchmarking
Live matplotlib dashboard.

Runs QAOA Wildfire Mitigation through the qBraid executor matrix
(balanced / aggressive) × (clifford / aer) and updates six
charts in real time as each run completes.

Usage (from repo root, venv active):
    python frontend/visualize.py
    python frontend/visualize.py --grid-rows 3 --grid-cols 3 --spsa-maxiter 10
    python frontend/visualize.py --strategies balanced aggressive --environments clifford aer
"""
from __future__ import annotations

import sys
from pathlib import Path

# ── Make src/ importable ───────────────────────────────────────────────────────
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import argparse
from typing import Any, Callable

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from executors import QBraidExecutor
from optimizers import SpsaOptimizer
from problems import WildfireMitigationProblem
from problems.base import Problem

# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Live qBraid QAOA Wildfire Mitigation benchmarking dashboard"
    )
    p.add_argument("--grid-rows",          type=int,   default=3)
    p.add_argument("--grid-cols",          type=int,   default=3)
    p.add_argument("--shrub-budget",       type=int,   default=3)
    p.add_argument("--brush-probability",  type=float, default=0.7)
    p.add_argument("--wildfire-seed",      type=int,   default=42)
    p.add_argument("--layer-reps",         type=int,   default=1)
    p.add_argument("--spsa-maxiter",       type=int,   default=20)
    p.add_argument("--backend",            default="ibm_rensselaer")
    p.add_argument("--qbraid-shots",       type=int,   default=1024)
    p.add_argument(
        "--strategies", nargs="+",
        default=["balanced", "aggressive"],
        choices=["balanced", "aggressive"],
        help="qBraid compilation strategies to compare.",
    )
    p.add_argument(
        "--environments", nargs="+",
        default=["clifford", "aer"],
        choices=["hardware", "aer", "clifford", "cloud"],
        help="Execution environments to run on.",
    )
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Live-problem wrapper — intercepts each loss iteration
# ─────────────────────────────────────────────────────────────────────────────

class _LiveProblem:
    """Wraps a Problem and injects a per-iteration loss callback into make_loss."""

    def __init__(self, problem: Problem, on_iteration: Callable[[float], None]) -> None:
        self._problem = problem
        self._on_iteration = on_iteration

    # Override only make_loss; everything else is delegated.
    def make_loss(self, *, problem_data, evaluator, experiment_results, iteration_times, logger):
        original = self._problem.make_loss(
            problem_data=problem_data,
            evaluator=evaluator,
            experiment_results=experiment_results,
            iteration_times=iteration_times,
            logger=logger,
        )
        cb = self._on_iteration

        def wrapped(params: np.ndarray) -> float:
            val = original(params)
            cb(float(val))
            return val

        return wrapped

    def __getattr__(self, name: str):
        return getattr(self._problem, name)


# ─────────────────────────────────────────────────────────────────────────────
# Palette / helpers
# ─────────────────────────────────────────────────────────────────────────────

_BG = "#161b22"
_COMBO_COLORS: dict[tuple[str, str], str] = {
    ("balanced",   "clifford"): "#00d4ff",  # cyan
    ("balanced",   "aer"):      "#10b981",  # green
    ("balanced",   "hardware"): "#8b5cf6",  # purple
    ("balanced",   "cloud"):    "#06b6d4",  # teal
    ("aggressive", "clifford"): "#f59e0b",  # amber
    ("aggressive", "aer"):      "#ef4444",  # red
    ("aggressive", "hardware"): "#ec4899",  # pink
    ("aggressive", "cloud"):    "#84cc16",  # lime
}
_ENV_MARKERS = {"clifford": "s", "aer": "o", "hardware": "D", "cloud": "^"}
_FALLBACK    = ["#00d4ff", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]


def _run_key(r: dict) -> str:
    return f"{r.get('strategy','?')}/{r.get('environment','?')}"


def _run_color(r: dict, idx: int) -> str:
    key = (r.get("strategy", ""), r.get("environment", ""))
    return _COMBO_COLORS.get(key, _FALLBACK[idx % len(_FALLBACK)])


# ─────────────────────────────────────────────────────────────────────────────
# Live dashboard
# ─────────────────────────────────────────────────────────────────────────────

class _Dashboard:
    """Six-panel matplotlib dashboard that updates live after every loss iteration."""

    _TITLE = (
        "qBraid Challenge — Compiler-Aware QAOA Wildfire Mitigation\n"
        "Strategy: balanced (opt-level 1)  vs  aggressive (opt-level 3)"
    )

    def __init__(self) -> None:
        plt.style.use("dark_background")
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.patch.set_facecolor("#0d1117")
        self.fig.suptitle(self._TITLE, fontsize=10, fontweight="bold", color="white")

        gs = gridspec.GridSpec(3, 3, figure=self.fig, hspace=0.62, wspace=0.42)
        self._ax_quality  = self.fig.add_subplot(gs[0, :2])
        self._ax_tradeoff = self.fig.add_subplot(gs[0, 2])
        self._ax_depth    = self.fig.add_subplot(gs[1, 0])
        self._ax_twoq     = self.fig.add_subplot(gs[1, 1])
        self._ax_approx   = self.fig.add_subplot(gs[1, 2])
        self._ax_loss     = self.fig.add_subplot(gs[2, :2])
        self._ax_strat    = self.fig.add_subplot(gs[2, 2])
        for ax in self.fig.get_axes():
            ax.set_facecolor(_BG)

        self._results: list[dict[str, Any]] = []
        self._cur_loss: list[float] = []
        self._cur_label: str = ""

        plt.ion()
        plt.tight_layout()
        plt.pause(0.05)

    # ── public API ────────────────────────────────────────────────────────────

    def set_current_run(self, label: str) -> None:
        self._cur_label = label
        self._cur_loss = []
        self._draw()

    def record_iteration(self, loss: float) -> None:
        self._cur_loss.append(loss)
        self._draw()

    def add_result(self, result: dict[str, Any]) -> None:
        exp = result.get("experiment_results") or []
        r = dict(result)
        r["loss_history"] = (
            [float(e["loss"]) for e in exp if "loss" in e] if exp else list(self._cur_loss)
        )
        self._results.append(r)
        self._cur_loss = []
        self._cur_label = ""
        self._draw()

    def finalize(self) -> None:
        plt.ioff()
        end_title = self._TITLE + "\n— benchmark complete —"
        self.fig.suptitle(end_title, fontsize=10, fontweight="bold", color="#10b981")
        self._draw()
        out = Path(__file__).resolve().parent / "benchmark_result.png"
        self.fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=self.fig.get_facecolor())
        print(f"\n[dashboard] saved → {out}")
        plt.show(block=True)

    # ── internal draw ─────────────────────────────────────────────────────────

    def _draw(self) -> None:
        rs = self._results
        cl = self._cur_loss
        lb = self._cur_label

        # ── 1. Quality scores ────────────────────────────────────────────────
        ax = self._ax_quality
        ax.cla(); ax.set_facecolor(_BG)
        if rs:
            keys   = [_run_key(r) for r in rs]
            scores = [r.get("quality_score", 0.0) for r in rs]
            cols   = [_run_color(r, i) for i, r in enumerate(rs)]
            bars   = ax.bar(keys, scores, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=7, color="white")
        ax.set_title("Output Quality — Fire-break score / quality score  (↑ better)", fontsize=8, fontweight="bold")
        ax.set_ylabel("Quality score", fontsize=7)
        ax.tick_params(axis="x", labelsize=7)
        ax.grid(axis="y", alpha=0.25)
        if lb:
            ax.set_xlabel(f"⏳ Running: {lb}", fontsize=7, color="#f59e0b")

        # ── 2. Quality vs compiled resource cost (tradeoff scatter) ──────────
        ax = self._ax_tradeoff
        ax.cla(); ax.set_facecolor(_BG)
        for i, r in enumerate(rs):
            ax.scatter(
                r.get("compiled_resource_cost", 0),
                r.get("quality_score", 0),
                color=_run_color(r, i),
                marker=_ENV_MARKERS.get(r.get("environment", ""), "o"),
                s=90, zorder=3,
                label=_run_key(r),
                edgecolors="white", linewidths=0.5,
            )
        if rs:
            ax.legend(fontsize=6, loc="best")
        ax.set_title("Quality vs Resource Cost", fontsize=8, fontweight="bold")
        ax.set_xlabel("Compiled resource cost  ↓", fontsize=7)
        ax.set_ylabel("Quality  ↑", fontsize=7)
        ax.grid(alpha=0.25)

        # ── 3. Circuit depth ─────────────────────────────────────────────────
        ax = self._ax_depth
        ax.cla(); ax.set_facecolor(_BG)
        if rs:
            keys = [_run_key(r) for r in rs]
            vals = [r.get("metrics", {}).get("depth", 0) for r in rs]
            cols = [_run_color(r, i) for i, r in enumerate(rs)]
            bars = ax.bar(keys, vals, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, padding=2, fontsize=7, color="white")
        ax.set_title("Circuit Depth  (↓ better)", fontsize=8, fontweight="bold")
        ax.tick_params(axis="x", labelsize=6)
        ax.grid(axis="y", alpha=0.25)

        # ── 4. 2-qubit gate count ────────────────────────────────────────────
        ax = self._ax_twoq
        ax.cla(); ax.set_facecolor(_BG)
        if rs:
            keys = [_run_key(r) for r in rs]
            vals = [r.get("metrics", {}).get("two_qubit_ops", 0) for r in rs]
            cols = [_run_color(r, i) for i, r in enumerate(rs)]
            bars = ax.bar(keys, vals, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, padding=2, fontsize=7, color="white")
        ax.set_title("2-Qubit Gate Count  (↓ better)", fontsize=8, fontweight="bold")
        ax.tick_params(axis="x", labelsize=6)
        ax.grid(axis="y", alpha=0.25)

        # ── 5. Relative approximation ratio ──────────────────────────────────
        ax = self._ax_approx
        ax.cla(); ax.set_facecolor(_BG)
        if rs:
            scores = [r.get("quality_score", 0.0) for r in rs]
            best   = max(scores) if scores else 1.0
            keys   = [_run_key(r) for r in rs]
            ratios = [s / max(best, 1e-9) for s in scores]
            cols   = ["#10b981" if v >= 0.99 else _run_color(r, i) for i, (r, v) in enumerate(zip(rs, ratios))]
            bars   = ax.bar(keys, ratios, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=7, color="white")
            ax.axhline(1.0, color="#10b981", linestyle="--", linewidth=1, label="best run")
            ax.legend(fontsize=6)
        ax.set_title("Approx. Ratio  (quality / best run)", fontsize=8, fontweight="bold")
        ax.tick_params(axis="x", labelsize=6)
        ax.set_ylim(0, 1.35)
        ax.grid(axis="y", alpha=0.25)

        # ── 6a. Loss convergence curve ───────────────────────────────────────
        ax = self._ax_loss
        ax.cla(); ax.set_facecolor(_BG)
        cycle = list(_COMBO_COLORS.values()) + _FALLBACK
        for i, r in enumerate(rs):
            hist = r.get("loss_history", [])
            if hist:
                ax.plot(hist, color=cycle[i % len(cycle)], linewidth=0.9,
                        alpha=0.75, label=_run_key(r))
        if cl:
            ax.plot(cl, color="#f59e0b", linewidth=1.6,
                    label=f"{lb} (live)" if lb else "current (live)")
        ax.set_title("Optimization Loss Convergence", fontsize=8, fontweight="bold")
        ax.set_xlabel("Iteration", fontsize=7)
        ax.set_ylabel("Loss", fontsize=7)
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(alpha=0.2)

        # ── 6b. Strategy summary scatter ─────────────────────────────────────
        ax = self._ax_strat
        ax.cla(); ax.set_facecolor(_BG)
        strat_color = {"balanced": "#00d4ff", "aggressive": "#ef4444"}
        for strat in ("balanced", "aggressive"):
            grp = [r for r in rs if r.get("strategy") == strat]
            if grp:
                aq = float(np.mean([r.get("quality_score", 0.0) for r in grp]))
                ac = float(np.mean([r.get("compiled_resource_cost", 0.0) for r in grp]))
                color = strat_color.get(strat, "#8b5cf6")
                ax.scatter(ac, aq, s=130, color=color, edgecolors="white",
                           linewidths=0.8, zorder=5)
                ax.annotate(
                    f" {strat}\n Q={aq:.1f}\n C={ac:.0f}",
                    (ac, aq), fontsize=7, color=color,
                    xytext=(6, 4), textcoords="offset points",
                )
        ax.set_title("Strategy Summary\n(avg across environments)", fontsize=8, fontweight="bold")
        ax.set_xlabel("Avg cost", fontsize=7)
        ax.set_ylabel("Avg quality", fontsize=7)
        ax.grid(alpha=0.25)

        self.fig.canvas.draw_idle()
        plt.pause(0.02)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _build_parser().parse_args()

    problem = WildfireMitigationProblem(
        grid_rows=args.grid_rows,
        grid_cols=args.grid_cols,
        shrub_budget=args.shrub_budget,
        brush_probability=args.brush_probability,
        seed=args.wildfire_seed,
        reps=max(1, args.layer_reps),
    )
    optimizer = SpsaOptimizer(
        maxiter=args.spsa_maxiter,
        learning_rate=0.2,
        perturbation=0.1,
        alpha=0.602,
        gamma=0.101,
        seed=args.wildfire_seed,
    )

    dash = _Dashboard()

    for strategy in args.strategies:
        for environment in args.environments:
            executor = QBraidExecutor(
                backend_name=args.backend,
                strategy=strategy,
                environment=environment,
                qbraid_shots=args.qbraid_shots,
            )
            label = f"{strategy}/{environment}"
            print(f"\n{'=' * 60}")
            print(f"  Running: {executor.run_label}")
            print(f"{'=' * 60}")

            dash.set_current_run(label)

            live_problem = _LiveProblem(
                problem,
                on_iteration=dash.record_iteration,
            )

            result = executor.execute(live_problem, optimizer=optimizer)
            result["combination"] = label
            dash.add_result(result)

    dash.finalize()


if __name__ == "__main__":
    main()
