"""Evaluation metrics for classical and quantum finance classifiers."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, roc_auc_score

from .constants import TRADING_DAYS_PER_YEAR


def safe_roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, scores))


def precision_at_top_decile(y_true: np.ndarray, scores: np.ndarray) -> float:
    if len(y_true) == 0:
        return float("nan")
    k = max(1, int(math.ceil(len(y_true) * 0.10)))
    order = np.argsort(scores)[::-1][:k]
    return float(np.mean(y_true[order]))


def signal_performance(predictions: np.ndarray, signal_returns: np.ndarray) -> Dict[str, float]:
    active_returns = signal_returns[predictions == 1]
    if len(active_returns) == 0:
        return {"signal_return_mean": 0.0, "signal_sharpe": 0.0, "max_drawdown": 0.0}
    mean_return = float(np.mean(active_returns))
    std_return = float(np.std(active_returns))
    sharpe = (mean_return / std_return) * math.sqrt(TRADING_DAYS_PER_YEAR / 5.0) if std_return > 0 else 0.0
    equity = np.cumprod(1.0 + active_returns)
    running_max = np.maximum.accumulate(equity)
    drawdowns = (equity - running_max) / np.maximum(running_max, 1e-12)
    return {
        "signal_return_mean": mean_return,
        "signal_sharpe": float(sharpe),
        "max_drawdown": float(np.min(drawdowns)) if len(drawdowns) else 0.0,
    }


def evaluate_classifier(
    *,
    y_true: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
    signal_returns: np.ndarray,
) -> Dict[str, Any]:
    metrics = {
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "roc_auc": safe_roc_auc(y_true, scores),
        "precision_top_decile": precision_at_top_decile(y_true, scores),
        "confusion_matrix": confusion_matrix(y_true, predictions, labels=[0, 1]).tolist(),
    }
    metrics.update(signal_performance(predictions, signal_returns))
    return metrics


def model_scores(model: Any, x_test: np.ndarray) -> np.ndarray:
    if hasattr(model, "predict_proba"):
        return np.asarray(model.predict_proba(x_test))[:, 1]
    if hasattr(model, "decision_function"):
        raw = np.asarray(model.decision_function(x_test), dtype=float)
        return 1.0 / (1.0 + np.exp(-raw))
    preds = np.asarray(model.predict(x_test), dtype=float)
    return preds


def metric_row(
    *,
    model: str,
    model_family: str,
    execution_mode: str,
    train_size: int,
    feature_dim: Optional[int],
    split_id: str,
    cutoff_date: Any,
    metrics: Dict[str, Any],
    train_seconds: float,
    infer_seconds: float,
    qubits: Optional[int] = None,
    kernel_circuit_depth: Optional[int] = None,
    kernel_two_qubit_gates: Optional[int] = None,
    shots: Optional[int] = None,
    selected_features: Optional[list[str]] = None,
    market_regime: str = "",
) -> Dict[str, Any]:
    return {
        "model": model,
        "model_family": model_family,
        "execution_mode": execution_mode,
        "train_size": int(train_size),
        "feature_dim": int(feature_dim) if feature_dim is not None else "",
        "split_id": split_id,
        "cutoff_date": str(cutoff_date)[:10],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "f1": metrics["f1"],
        "roc_auc": metrics["roc_auc"],
        "precision_top_decile": metrics["precision_top_decile"],
        "signal_return_mean": metrics["signal_return_mean"],
        "signal_sharpe": metrics["signal_sharpe"],
        "max_drawdown": metrics["max_drawdown"],
        "train_seconds": train_seconds,
        "infer_seconds": infer_seconds,
        "qubits": int(qubits) if qubits is not None else "",
        "kernel_circuit_depth": int(kernel_circuit_depth) if kernel_circuit_depth is not None else "",
        "kernel_two_qubit_gates": int(kernel_two_qubit_gates) if kernel_two_qubit_gates is not None else "",
        "shots": int(shots) if shots is not None else "",
        "selected_features": ",".join(selected_features or []),
        "market_regime": market_regime,
        "confusion_matrix": metrics["confusion_matrix"],
    }
