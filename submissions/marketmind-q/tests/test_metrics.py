from __future__ import annotations

import numpy as np

from src.metrics import evaluate_classifier, precision_at_top_decile, signal_performance


def test_precision_at_top_decile_uses_highest_scores():
    y_true = np.array([0, 0, 1, 1, 1, 0, 0, 1, 0, 1])
    scores = np.array([0.1, 0.2, 0.99, 0.8, 0.7, 0.3, 0.4, 0.6, 0.5, 0.9])
    assert precision_at_top_decile(y_true, scores) == 1.0


def test_signal_performance_known_values():
    predictions = np.array([1, 0, 1, 0])
    returns = np.array([0.01, -0.5, -0.02, 0.9])
    result = signal_performance(predictions, returns)
    assert result["signal_return_mean"] == -0.005
    assert result["max_drawdown"] < 0


def test_evaluate_classifier_returns_expected_metric_keys():
    y_true = np.array([0, 1, 0, 1])
    predictions = np.array([0, 1, 1, 1])
    scores = np.array([0.1, 0.8, 0.7, 0.9])
    returns = np.array([-0.01, 0.02, -0.03, 0.04])
    result = evaluate_classifier(y_true=y_true, predictions=predictions, scores=scores, signal_returns=returns)
    assert result["balanced_accuracy"] == 0.75
    assert result["f1"] > 0
    assert result["roc_auc"] == 1.0
    assert result["confusion_matrix"] == [[1, 1], [0, 2]]

