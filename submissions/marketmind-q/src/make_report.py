"""Generate MarketMind-Q figures and summary artifacts."""

from __future__ import annotations

import argparse
import ast
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .config import load_config, project_path
from .constants import PROJECT_ROOT


def _load_plotting():
    cache_dir = PROJECT_ROOT / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(cache_dir / "matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir))
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import seaborn as sns
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("matplotlib and seaborn are required for report generation.") from exc
    sns.set_theme(style="whitegrid", context="talk")
    return plt, sns


def _save(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")


def _best_classical(metrics: pd.DataFrame) -> pd.DataFrame:
    classical = metrics[metrics["model_family"] == "classical"].copy()
    group_cols = ["train_size", "split_id"]
    idx = classical.groupby(group_cols)["roc_auc"].idxmax()
    return classical.loc[idx].rename(columns={"roc_auc": "best_classical_roc_auc"})


def plot_qml_edge(metrics: pd.DataFrame, figures_dir: Path) -> Path:
    plt, sns = _load_plotting()
    quantum = metrics[(metrics["model_family"] == "quantum") & (metrics["execution_mode"] == "statevector_exact")].copy()
    if quantum.empty:
        raise ValueError("No statevector_exact quantum rows available.")
    best_classical = _best_classical(metrics)[["train_size", "split_id", "best_classical_roc_auc"]]
    merged = quantum.merge(best_classical, on=["train_size", "split_id"], how="inner")
    merged["qml_edge"] = merged["roc_auc"] - merged["best_classical_roc_auc"]
    pivot = merged.pivot_table(index="train_size", columns="feature_dim", values="qml_edge", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(pivot, annot=True, fmt=".3f", center=0.0, cmap="vlag", ax=ax)
    ax.set_title("Quantum kernel ROC-AUC edge vs best classical")
    ax.set_xlabel("Quantum feature dimension")
    ax.set_ylabel("Training samples")
    output = figures_dir / "qml_edge_heatmap.png"
    _save(fig, output)
    plt.close(fig)
    return output


def plot_regime_breakdown(metrics: pd.DataFrame, figures_dir: Path) -> Path:
    plt, sns = _load_plotting()
    rows = metrics.copy()
    rows["label"] = np.where(
        rows["model_family"] == "quantum",
        rows["model"] + " / " + rows["execution_mode"],
        rows["model"],
    )
    keep = rows[
        rows["label"].isin(["quantum_kernel_svm / statevector_exact", "rbf_svm", "xgboost", "random_forest", "logistic_regression"])
    ].copy()
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=keep, x="market_regime", y="roc_auc", hue="label", errorbar=None, ax=ax)
    ax.set_title("Performance by market volatility regime")
    ax.set_xlabel("Market regime")
    ax.set_ylabel("ROC-AUC")
    ax.legend(loc="best", fontsize="small")
    output = figures_dir / "regime_breakdown.png"
    _save(fig, output)
    plt.close(fig)
    return output


def _parse_confusion(value) -> np.ndarray:
    if isinstance(value, list):
        return np.asarray(value)
    return np.asarray(ast.literal_eval(str(value)))


def plot_confusion_matrices(metrics: pd.DataFrame, figures_dir: Path) -> Path:
    plt, sns = _load_plotting()
    candidates = []
    classical = metrics[metrics["model_family"] == "classical"].copy()
    quantum = metrics[(metrics["model_family"] == "quantum") & (metrics["execution_mode"] == "statevector_exact")].copy()
    if not classical.empty:
        candidates.append(("Best classical", classical.loc[classical["roc_auc"].idxmax()]))
    if not quantum.empty:
        candidates.append(("Best quantum kernel", quantum.loc[quantum["roc_auc"].idxmax()]))
    if not candidates:
        raise ValueError("No rows available for confusion matrices.")
    fig, axes = plt.subplots(1, len(candidates), figsize=(6 * len(candidates), 5))
    if len(candidates) == 1:
        axes = [axes]
    for ax, (title, row) in zip(axes, candidates):
        matrix = _parse_confusion(row["confusion_matrix"])
        sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
        ax.set_title(f"{title}: {row['model']} ({row['execution_mode']})")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
    output = figures_dir / "confusion_matrices.png"
    _save(fig, output)
    plt.close(fig)
    return output


def plot_equity_curve(metrics: pd.DataFrame, figures_dir: Path) -> Path:
    plt, _ = _load_plotting()
    selected = metrics[
        ((metrics["model_family"] == "classical") & (metrics["model"].isin(["rbf_svm", "xgboost", "random_forest"])))
        | ((metrics["model_family"] == "quantum") & (metrics["execution_mode"] == "statevector_exact"))
    ].copy()
    if selected.empty:
        raise ValueError("No rows available for equity curve.")
    selected["label"] = np.where(
        selected["model_family"] == "quantum",
        "quantum_kernel_svm",
        selected["model"],
    )
    curve = (
        selected.groupby(["label", "cutoff_date"], as_index=False)["signal_return_mean"]
        .mean()
        .sort_values(["label", "cutoff_date"])
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, group in curve.groupby("label"):
        equity = (1.0 + group["signal_return_mean"].to_numpy(dtype=float)).cumprod()
        ax.plot(pd.to_datetime(group["cutoff_date"]), equity, marker="o", label=label)
    ax.set_title("Top-signal strategy equity proxy")
    ax.set_xlabel("Cutoff date")
    ax.set_ylabel("Cumulative growth")
    ax.legend(loc="best", fontsize="small")
    output = figures_dir / "equity_curve.png"
    _save(fig, output)
    plt.close(fig)
    return output


def plot_score_cost_frontier(metrics: pd.DataFrame, figures_dir: Path) -> Path:
    plt, sns = _load_plotting()
    quantum = metrics[metrics["model_family"] == "quantum"].copy()
    if quantum.empty:
        raise ValueError("No quantum rows available for score/cost frontier.")
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(
        data=quantum,
        x="kernel_two_qubit_gates",
        y="roc_auc",
        hue="execution_mode",
        size="train_size",
        style="feature_dim",
        ax=ax,
    )
    ax.set_title("Quantum score vs compiled two-qubit cost")
    ax.set_xlabel("Kernel circuit two-qubit gates")
    ax.set_ylabel("ROC-AUC")
    output = figures_dir / "score_cost_frontier.png"
    _save(fig, output)
    plt.close(fig)
    return output


def write_summary(
    metrics: pd.DataFrame,
    figures: Iterable[Path],
    output_path: Path,
    qbraid_metrics: pd.DataFrame | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    top_rows = metrics.sort_values("roc_auc", ascending=False).head(8)
    best_quantum = metrics[metrics["model_family"] == "quantum"].sort_values("roc_auc", ascending=False).head(1)
    best_classical = metrics[metrics["model_family"] == "classical"].sort_values("roc_auc", ascending=False).head(1)
    lines = [
        "# MarketMind-Q Results Summary",
        "",
        "This report is generated from `python -m src.make_report`.",
        "",
        "## Best Classical",
        "",
        best_classical.to_markdown(index=False) if not best_classical.empty else "No classical rows.",
        "",
        "## Best Quantum",
        "",
        best_quantum.to_markdown(index=False) if not best_quantum.empty else "No quantum rows.",
        "",
        "## Top Rows By ROC-AUC",
        "",
        top_rows.to_markdown(index=False),
        "",
    ]
    if qbraid_metrics is not None and not qbraid_metrics.empty:
        successful = qbraid_metrics[qbraid_metrics["status"] == "success"].copy()
        if not successful.empty:
            qbraid_summary = successful.groupby(["strategy", "execution_environment"], as_index=False).agg(
                rows=("status", "count"),
                mean_abs_probability_error=("abs_probability_error", "mean"),
                max_abs_probability_error=("abs_probability_error", "max"),
                mean_hellinger_distance=("hellinger_distance", "mean"),
                mean_depth=("depth", "mean"),
                mean_two_qubit_gates=("two_qubit_gates", "mean"),
            )
            lines.extend(
                [
                    "## qBraid Compiler-Aware Results",
                    "",
                    qbraid_summary.to_markdown(index=False),
                    "",
                ]
            )
    lines.extend(["## Figures", ""])
    lines.extend(f"- `{path}`" for path in figures)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def make_report(config: dict, *, root: Path = PROJECT_ROOT) -> list[Path]:
    metrics_path = project_path(config["metrics_path"], root=root)
    figures_dir = project_path(config["figures_dir"], root=root)
    summary_path = project_path(config["summary_path"], root=root)
    metrics = pd.read_csv(metrics_path)
    figures = [
        plot_qml_edge(metrics, figures_dir),
        plot_regime_breakdown(metrics, figures_dir),
        plot_confusion_matrices(metrics, figures_dir),
        plot_equity_curve(metrics, figures_dir),
        plot_score_cost_frontier(metrics, figures_dir),
    ]
    qbraid_metrics_path = project_path(config.get("qbraid_metrics_path", "results/qbraid_compile_metrics.csv"), root=root)
    qbraid_metrics = pd.read_csv(qbraid_metrics_path) if qbraid_metrics_path.exists() else None
    for figure_name in ["qbraid_quality_cost.png", "qbraid_strategy_resources.png"]:
        qbraid_figure = figures_dir / figure_name
        if qbraid_figure.exists():
            figures.append(qbraid_figure)
    write_summary(metrics, figures, summary_path, qbraid_metrics=qbraid_metrics)
    return figures


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate MarketMind-Q report figures.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "sector_etf.yaml"))
    args = parser.parse_args()
    figures = make_report(load_config(args.config))
    print("Generated figures:")
    for figure in figures:
        print(f"  {figure}")


if __name__ == "__main__":
    main()
