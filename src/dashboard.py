"""Live qBraid matrix dashboard helpers for wildfire benchmark runs.

This module is imported by `src/main.py` to decorate qBraid matrix runs.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import numpy as np

from executors import QBraidExecutor
from problems.base import Problem

_BG = "#161b22"
_COMBO_COLORS: dict[tuple[str, str], str] = {
    ("balanced", "clifford"): "#00d4ff",
    ("balanced", "aer"): "#10b981",
    ("balanced", "hardware"): "#8b5cf6",
    ("balanced", "cloud"): "#06b6d4",
    ("aggressive", "clifford"): "#f59e0b",
    ("aggressive", "aer"): "#ef4444",
    ("aggressive", "hardware"): "#ec4899",
    ("aggressive", "cloud"): "#84cc16",
}
_ENV_MARKERS = {"clifford": "s", "aer": "o", "hardware": "D", "cloud": "^"}
_FALLBACK = ["#00d4ff", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]


class LiveProblem(Problem):
    """Wrap a Problem and invoke a callback after each loss evaluation."""

    @classmethod
    def add_cli_arguments(cls, parser) -> None:
        _ = parser

    @classmethod
    def from_namespace(cls, args):
        raise NotImplementedError("LiveProblem is a runtime wrapper and cannot be built from CLI args.")

    def __init__(self, problem: Problem, on_iteration: Callable[[float], None]) -> None:
        self._problem = problem
        self._on_iteration = on_iteration

    def build_problem_data(self, *, logger):
        return self._problem.build_problem_data(logger=logger)

    def build_ansatz(self, *, logger):
        return self._problem.build_ansatz(logger=logger)

    def build_observables(self, layout: Any, problem_data: Any) -> list[list[Any]]:
        return self._problem.build_observables(layout, problem_data)

    def metric_candidates(self) -> tuple[str, ...]:
        return self._problem.metric_candidates()

    def describe_parameters(self, params: np.ndarray) -> dict[str, Any]:
        return self._problem.describe_parameters(params)

    def postprocess(self, *, problem_data: Any, experiment_results: list[dict[str, Any]]) -> dict[str, Any]:
        return self._problem.postprocess(problem_data=problem_data, experiment_results=experiment_results)

    def make_loss(self, *, problem_data, evaluator, experiment_results, iteration_times, logger):
        original = self._problem.make_loss(
            problem_data=problem_data,
            evaluator=evaluator,
            experiment_results=experiment_results,
            iteration_times=iteration_times,
            logger=logger,
        )

        def wrapped(params: np.ndarray) -> float:
            value = original(params)
            self._on_iteration(float(value))
            return value

        return wrapped

    def __getattr__(self, name: str):
        return getattr(self._problem, name)


def _run_key(result: dict) -> str:
    env = result.get("environment", "?")
    tag = " \u2605" if env in ("hardware", "cloud") else ""
    return f"{result.get('strategy', '?')}/{env}{tag}"


def _run_color(result: dict, idx: int) -> str:
    key = (result.get("strategy", ""), result.get("environment", ""))
    return _COMBO_COLORS.get(key, _FALLBACK[idx % len(_FALLBACK)])


class BenchmarkDashboard:
    """Six-panel matplotlib dashboard that updates after every qBraid iteration."""

    _TITLE = (
        "qBraid Challenge — Compiler-Aware QAOA Wildfire Mitigation\n"
        "Strategy: balanced (opt-level 1)  vs  aggressive (opt-level 3)"
    )

    def __init__(self) -> None:
        with plt.style.context("dark_background"):
            self.fig = plt.figure(figsize=(16, 10))
            self.fig.patch.set_facecolor("#0d1117")
            self.fig.suptitle(self._TITLE, fontsize=10, fontweight="bold", color="white")

            gs = gridspec.GridSpec(3, 3, figure=self.fig, hspace=0.62, wspace=0.42)
            self._ax_quality = self.fig.add_subplot(gs[0, :2])
            self._ax_tradeoff = self.fig.add_subplot(gs[0, 2])
            self._ax_depth = self.fig.add_subplot(gs[1, 0])
            self._ax_twoq = self.fig.add_subplot(gs[1, 1])
            self._ax_approx = self.fig.add_subplot(gs[1, 2])
            self._ax_loss = self.fig.add_subplot(gs[2, :2])
            self._ax_strat = self.fig.add_subplot(gs[2, 2])
            for ax in self.fig.get_axes():
                ax.set_facecolor(_BG)

        self._results: list[dict[str, Any]] = []
        self._cur_loss: list[float] = []
        self._cur_label = ""

        self._lock = threading.Lock()
        self._pending_qpu: list[dict[str, Any]] = []
        self._qpu_run_config: dict[str, Any] | None = None
        self._qpu_thread: threading.Thread | None = None
        self._btn_qpu: Button | None = None
        self._ax_btn = None
        self._on_hardware_result: Callable[[dict[str, Any]], None] | None = None

        self.fig.subplots_adjust(top=0.92, bottom=0.10, left=0.07, right=0.97)
        plt.ion()
        plt.pause(0.05)

    def set_current_run(self, label: str) -> None:
        self._cur_label = label
        self._cur_loss = []
        self._draw()

    def record_iteration(self, loss: float) -> None:
        self._cur_loss.append(loss)
        self._draw()

    def add_result(self, result: dict[str, Any]) -> None:
        exp = result.get("experiment_results") or []
        enriched = dict(result)
        enriched["loss_history"] = (
            [float(entry["loss"]) for entry in exp if "loss" in entry] if exp else list(self._cur_loss)
        )
        self._results.append(enriched)
        self._cur_loss = []
        self._cur_label = ""
        self._draw()

    def setup_qpu(
        self,
        problem: Problem,
        optimizer,
        backend: str,
        shots: int,
        strategies: list[str],
        on_result: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        unique_strategies = list(dict.fromkeys(strategies))
        self._qpu_run_config = dict(
            problem=problem,
            optimizer=optimizer,
            backend=backend,
            shots=shots,
            strategies=unique_strategies,
        )
        self._on_hardware_result = on_result

    def _on_qpu_click(self, _event) -> None:
        if self._qpu_run_config is None:
            return
        if self._qpu_thread is not None and self._qpu_thread.is_alive():
            return
        if self._btn_qpu is not None:
            self._btn_qpu.label.set_text("⏳  Running on QPU hardware…")
            self._btn_qpu.color = "#2d1800"
        self.fig.canvas.draw_idle()
        self._qpu_thread = threading.Thread(target=self._qpu_run_bg, daemon=True)
        self._qpu_thread.start()

    def _qpu_run_bg(self) -> None:
        cfg = self._qpu_run_config
        if cfg is None:
            return

        for strategy in cfg["strategies"]:
            label = f"{strategy}/hardware"
            with self._lock:
                self._pending_qpu.append({"type": "label", "label": label})

            try:
                loss_buf: list[float] = []

                def on_iter(loss: float, _lbl: str = label) -> None:
                    loss_buf.append(loss)
                    with self._lock:
                        self._pending_qpu.append(
                            {"type": "iteration", "loss": loss, "label": _lbl}
                        )

                executor = QBraidExecutor(
                    backend_name=cfg["backend"],
                    strategy=strategy,
                    environment="hardware",
                    qbraid_shots=cfg["shots"],
                )
                live = LiveProblem(cfg["problem"], on_iteration=on_iter)
                result = executor.execute(live, optimizer=cfg["optimizer"])
                result["combination"] = label
                if not result.get("loss_history"):
                    result["loss_history"] = list(loss_buf)
                with self._lock:
                    self._pending_qpu.append({"type": "result", "result": result})
            except Exception as exc:  # noqa: BLE001
                with self._lock:
                    self._pending_qpu.append({"type": "error", "label": label, "msg": str(exc)})

        with self._lock:
            self._pending_qpu.append({"type": "done"})

    def _poll_qpu_data(self) -> None:
        with self._lock:
            items, self._pending_qpu = list(self._pending_qpu), []

        if not items:
            return

        changed = False
        for item in items:
            kind = item["type"]
            if kind == "label":
                self._cur_label = item["label"]
                self._cur_loss = []
                changed = True
            elif kind == "iteration":
                self._cur_loss.append(item["loss"])
                changed = True
            elif kind == "result":
                result = item["result"]
                if not result.get("loss_history"):
                    result["loss_history"] = list(self._cur_loss)
                self._results.append(result)
                if self._on_hardware_result is not None:
                    self._on_hardware_result(result)
                self._cur_loss = []
                self._cur_label = ""
                changed = True
            elif kind == "error":
                print(f"\n[QPU Error] {item['label']}: {item['msg']}")
                print(
                    "[QPU] Make sure IBM Quantum credentials are saved via QiskitRuntimeService.save_account()."
                )
                self._cur_label = ""
                changed = True
            elif kind == "done":
                if self._btn_qpu is not None:
                    self._btn_qpu.label.set_text("✓  QPU run complete — results added to charts")
                    self._btn_qpu.color = "#0d2b1a"
                changed = True

        if changed:
            self._draw(_pause=False)

    def finalize(self, *, block: bool = True, show_hardware_button: bool = True) -> plt.Figure:
        plt.ioff()
        end_title = self._TITLE + "\n— benchmark complete —"
        if show_hardware_button and self._qpu_run_config and self._qpu_run_config.get("strategies"):
            end_title += "  (click button below to run on real QPU)"
        self.fig.suptitle(end_title, fontsize=10, fontweight="bold", color="white")
        self._draw()

        out = Path(__file__).resolve().parent / "benchmark_result.png"
        self.fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=self.fig.get_facecolor())
        print(f"\n[dashboard] saved → {out}")

        if show_hardware_button and self._qpu_run_config and self._qpu_run_config.get("strategies"):
            self._ax_btn = self.fig.add_axes((0.35, 0.015, 0.30, 0.050))
            self._btn_qpu = Button(
                self._ax_btn,
                "▶  Run on QPU  (real hardware)",
                color="#1a2035",
                hovercolor="#2d3a52",
            )
            self._btn_qpu.label.set_color("white")
            self._btn_qpu.label.set_fontsize(9)
            self._btn_qpu.label.set_fontweight("bold")
            self._btn_qpu.on_clicked(self._on_qpu_click)

            self._qpu_timer = self.fig.canvas.new_timer(interval=200)
            self._qpu_timer.add_callback(self._poll_qpu_data)
            self._qpu_timer.start()

        self.fig.canvas.draw_idle()
        plt.show(block=block)
        if not block:
            plt.pause(0.05)
        return self.fig

    def _draw(self, *, _pause: bool = True) -> None:
        results = self._results
        current_loss = self._cur_loss
        current_label = self._cur_label

        ax = self._ax_quality
        ax.cla(); ax.set_facecolor(_BG)
        if results:
            keys = [_run_key(result) for result in results]
            scores = [result.get("quality_score", 0.0) for result in results]
            cols = [_run_color(result, index) for index, result in enumerate(results)]
            bars = ax.bar(keys, scores, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=7, color="white")
        ax.set_title("Output Quality — Fire-break score / quality score  (↑ better)", fontsize=8, fontweight="bold", color="white")
        ax.set_ylabel("Quality score", fontsize=7, color="white")
        ax.tick_params(axis="x", labelsize=7, colors="white")
        ax.tick_params(axis="y", colors="white")
        ax.grid(axis="y", alpha=0.25)
        if current_label:
            ax.set_xlabel(f"⏳ Running: {current_label}", fontsize=7, color="white")

        ax = self._ax_tradeoff
        ax.cla(); ax.set_facecolor(_BG)
        for index, result in enumerate(results):
            ax.scatter(
                result.get("compiled_resource_cost", 0),
                result.get("quality_score", 0),
                color=_run_color(result, index),
                marker=_ENV_MARKERS.get(result.get("environment", ""), "o"),
                s=90,
                zorder=3,
                label=_run_key(result),
                edgecolors="white",
                linewidths=0.5,
            )
        if results:
            legend = ax.legend(fontsize=6, loc="best")
            for text in legend.get_texts():
                text.set_color("white")
        ax.set_title("Quality vs Resource Cost", fontsize=8, fontweight="bold", color="white")
        ax.set_xlabel("Compiled resource cost  ↓", fontsize=7, color="white")
        ax.set_ylabel("Quality  ↑", fontsize=7, color="white")
        ax.tick_params(axis="both", colors="white")
        ax.grid(alpha=0.25)

        ax = self._ax_depth
        ax.cla(); ax.set_facecolor(_BG)
        if results:
            keys = [_run_key(result) for result in results]
            vals = [result.get("metrics", {}).get("depth", 0) for result in results]
            cols = [_run_color(result, index) for index, result in enumerate(results)]
            bars = ax.bar(keys, vals, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, padding=2, fontsize=7, color="white")
        ax.set_title("Circuit Depth  (↓ better)", fontsize=8, fontweight="bold", color="white")
        ax.tick_params(axis="x", labelsize=6, colors="white")
        ax.tick_params(axis="y", colors="white")
        ax.grid(axis="y", alpha=0.25)

        ax = self._ax_twoq
        ax.cla(); ax.set_facecolor(_BG)
        if results:
            keys = [_run_key(result) for result in results]
            vals = [result.get("metrics", {}).get("two_qubit_ops", 0) for result in results]
            cols = [_run_color(result, index) for index, result in enumerate(results)]
            bars = ax.bar(keys, vals, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, padding=2, fontsize=7, color="white")
        ax.set_title("2-Qubit Gate Count  (↓ better)", fontsize=8, fontweight="bold", color="white")
        ax.tick_params(axis="x", labelsize=6, colors="white")
        ax.tick_params(axis="y", colors="white")
        ax.grid(axis="y", alpha=0.25)

        ax = self._ax_approx
        ax.cla(); ax.set_facecolor(_BG)
        if results:
            scores = [result.get("quality_score", 0.0) for result in results]
            best = max(scores) if scores else 1.0
            keys = [_run_key(result) for result in results]
            ratios = [score / max(best, 1e-9) for score in scores]
            cols = [_run_color(result, index) for index, result in enumerate(results)]
            bars = ax.bar(keys, ratios, color=cols, edgecolor="white", linewidth=0.4)
            ax.bar_label(bars, fmt="%.3f", padding=2, fontsize=7, color="white")
            ax.axhline(1.0, color="#10b981", linestyle="--", linewidth=1, label="best run")
            legend = ax.legend(fontsize=6)
            for text in legend.get_texts():
                text.set_color("white")
        ax.set_title("Approx. Ratio  (quality / best run)", fontsize=8, fontweight="bold", color="white")
        ax.tick_params(axis="x", labelsize=6, colors="white")
        ax.tick_params(axis="y", colors="white")
        ax.set_ylim(0, 1.35)
        ax.grid(axis="y", alpha=0.25)

        ax = self._ax_loss
        ax.cla(); ax.set_facecolor(_BG)
        for index, result in enumerate(results):
            history = result.get("loss_history", [])
            if history:
                ax.plot(
                    history,
                    color=_run_color(result, index),
                    linewidth=0.9,
                    alpha=0.75,
                    label=_run_key(result),
                )
        if current_loss:
            live_color = _COMBO_COLORS.get(
                (current_label.split("/")[0], current_label.split("/")[-1]) if "/" in current_label else ("", ""),
                "#f59e0b",
            )
            ax.plot(
                current_loss,
                color=live_color,
                linewidth=1.6,
                label=f"{current_label} (live)" if current_label else "current (live)",
            )
        ax.set_title("Optimization Loss Convergence", fontsize=8, fontweight="bold", color="white")
        ax.set_xlabel("Iteration", fontsize=7, color="white")
        ax.set_ylabel("Loss", fontsize=7, color="white")
        ax.tick_params(axis="both", colors="white")
        if results or current_loss:
            legend = ax.legend(fontsize=7, loc="upper right")
            for text in legend.get_texts():
                text.set_color("white")
        ax.grid(alpha=0.2)

        ax = self._ax_strat
        ax.cla(); ax.set_facecolor(_BG)
        first_colors = {"balanced": "#00d4ff", "aggressive": "#f59e0b"}
        for strategy in ("balanced", "aggressive"):
            group = [result for result in results if result.get("strategy") == strategy]
            if group:
                avg_quality = float(np.mean([result.get("quality_score", 0.0) for result in group]))
                avg_cost = float(np.mean([result.get("compiled_resource_cost", 0.0) for result in group]))
                color = first_colors.get(strategy, "#8b5cf6")
                ax.scatter(avg_cost, avg_quality, s=130, color=color, edgecolors="white", linewidths=0.8, zorder=5)
                ax.annotate(
                    f" {strategy}\n Q={avg_quality:.1f}\n C={avg_cost:.0f}",
                    (avg_cost, avg_quality),
                    fontsize=7,
                    color="white",
                    xytext=(6, 4),
                    textcoords="offset points",
                )
        ax.set_title("Strategy Summary\n(avg across environments)", fontsize=8, fontweight="bold", color="white")
        ax.set_xlabel("Avg cost", fontsize=7, color="white")
        ax.set_ylabel("Avg quality", fontsize=7, color="white")
        ax.tick_params(axis="both", colors="white")
        ax.grid(alpha=0.25)

        self.fig.canvas.draw_idle()
        if _pause:
            plt.pause(0.02)

