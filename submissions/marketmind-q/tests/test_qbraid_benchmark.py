from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.constants import FEATURE_COLUMNS
from src.qbraid_benchmark import (
    cirq_direct_rows,
    deterministic_kernel_pairs,
    hellinger_bernoulli,
    qasm2_roundtrip_rows,
    qiskit_resource_metrics,
    reconstruct_best_split,
    select_best_quantum_row,
)
from src.quantum_kernel import make_compute_uncompute_circuit


def test_select_best_quantum_row_uses_statevector_roc_auc():
    metrics = pd.DataFrame(
        [
            {"model": "quantum_kernel_svm", "model_family": "quantum", "execution_mode": "shots_1024", "roc_auc": 0.99},
            {"model": "quantum_kernel_svm", "model_family": "quantum", "execution_mode": "statevector_exact", "roc_auc": 0.51},
            {"model": "quantum_kernel_svm", "model_family": "quantum", "execution_mode": "statevector_exact", "roc_auc": 0.72},
        ]
    )
    row = select_best_quantum_row(metrics)
    assert row["roc_auc"] == 0.72
    assert row["execution_mode"] == "statevector_exact"


def test_hellinger_bernoulli_zero_for_identical_positive_for_different():
    assert hellinger_bernoulli(0.25, 0.25) == 0.0
    assert hellinger_bernoulli(0.25, 0.75) > 0.0


def test_deterministic_kernel_pairs_are_stable():
    x_train = np.arange(20, dtype=float).reshape(10, 2)
    x_test = np.arange(12, dtype=float).reshape(6, 2)
    first = deterministic_kernel_pairs(x_train, x_test, max_train_pairs=3, max_test_pairs=2)
    second = deterministic_kernel_pairs(x_train, x_test, max_train_pairs=3, max_test_pairs=2)
    assert [pair.pair_id for pair in first] == [pair.pair_id for pair in second]
    assert [pair.pair_kind for pair in first] == ["train_train", "train_train", "train_train", "test_train", "test_train"]


def test_qiskit_resource_metrics_are_nonzero_for_kernel_circuit():
    circuit = make_compute_uncompute_circuit(np.array([0.2, 0.7]), np.array([1.1, 0.4]))
    metrics = qiskit_resource_metrics(circuit)
    assert metrics["qubits"] == 2
    assert metrics["depth"] > 0
    assert metrics["two_qubit_gates"] > 0
    assert metrics["measurement_count"] == 2


def _frozen_dataset(path):
    dates = pd.bdate_range("2022-01-03", periods=180)
    rows = []
    for ticker_offset, ticker in enumerate(["XLF", "XLK"]):
        for idx, date in enumerate(dates):
            target = (idx + ticker_offset) % 2
            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "close": 100 + idx + ticker_offset,
                    "volume": 1000 + idx,
                    "forward_return_5d": 0.01 if target else -0.01,
                    "spy_forward_return_5d": 0.0,
                    "excess_return_5d": 0.01 if target else -0.01,
                    "target": target,
                    **{column: float((idx % 17) + feature_idx + ticker_offset) for feature_idx, column in enumerate(FEATURE_COLUMNS)},
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_reconstruct_best_split_from_metrics(tmp_path):
    dataset_path = tmp_path / "data" / "dataset.csv"
    metrics_path = tmp_path / "results" / "metrics.csv"
    _frozen_dataset(dataset_path)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "model": "quantum_kernel_svm",
                "model_family": "quantum",
                "execution_mode": "statevector_exact",
                "train_size": 40,
                "feature_dim": 2,
                "split_id": "split_00_train_40",
                "roc_auc": 0.6,
            }
        ]
    ).to_csv(metrics_path, index=False)
    config = {
        "dataset_path": str(dataset_path),
        "metrics_path": str(metrics_path),
        "tickers": ["XLF", "XLK"],
        "cutoffs": ["2022-06-01"],
        "test_days": 10,
    }
    bundle, prepared, best = reconstruct_best_split(config, root=tmp_path)
    assert bundle.split_id == "split_00_train_40"
    assert prepared.x_train_quantum.shape[1] == 2
    assert best["roc_auc"] == 0.6


def test_qbraid_qasm2_roundtrip_smoke():
    pytest.importorskip("qbraid")
    source = make_compute_uncompute_circuit(np.array([0.2, 0.7]), np.array([1.1, 0.4]))
    best = pd.Series({"split_id": "split_00_train_40", "train_size": 40, "feature_dim": 2, "roc_auc": 0.6})
    pair = deterministic_kernel_pairs(np.array([[0.2, 0.7], [1.1, 0.4]]), np.array([[0.5, 0.6]]), max_train_pairs=1, max_test_pairs=0)[0]
    rows = qasm2_roundtrip_rows(pair, source, 0.5, shots=32, selected_features=["a", "b"], best_row=best)
    assert rows
    assert all(row["strategy"] == "qasm2_roundtrip" for row in rows)
    assert all(row["status"] == "success" for row in rows)


def test_qbraid_cirq_direct_smoke():
    pytest.importorskip("qbraid")
    pytest.importorskip("cirq")
    source = make_compute_uncompute_circuit(np.array([0.2, 0.7]), np.array([1.1, 0.4]))
    best = pd.Series({"split_id": "split_00_train_40", "train_size": 40, "feature_dim": 2, "roc_auc": 0.6})
    pair = deterministic_kernel_pairs(np.array([[0.2, 0.7], [1.1, 0.4]]), np.array([[0.5, 0.6]]), max_train_pairs=1, max_test_pairs=0)[0]
    rows = cirq_direct_rows(pair, source, 0.5, shots=32, selected_features=["a", "b"], best_row=best)
    assert rows
    assert all(row["strategy"] == "cirq_direct" for row in rows)
    assert all(row["status"] == "success" for row in rows)

