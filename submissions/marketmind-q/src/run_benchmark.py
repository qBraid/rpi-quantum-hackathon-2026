"""Run the MarketMind-Q classical and quantum benchmark."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
from sklearn.svm import SVC

from .classical_models import build_classical_models
from .config import load_config, project_path
from .constants import DEFAULT_CUTOFFS, FEATURE_DIMS, PROJECT_ROOT, RANDOM_STATE, TEST_DAYS, TRAIN_SIZES
from .features import read_dataset
from .metrics import evaluate_classifier, metric_row, model_scores
from .quantum_kernel import compute_quantum_kernel_bundle
from .splits import make_walk_forward_splits, prepare_features, split_signal_returns


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _filter_rows(dataset: pd.DataFrame, tickers: Iterable[str] | None) -> pd.DataFrame:
    if not tickers:
        return dataset
    return dataset[dataset["ticker"].isin(list(tickers))].copy()


def _market_regime(test: pd.DataFrame, volatility_threshold: float) -> str:
    realized = float(test["spy_vol_20d"].median())
    return "high_volatility" if realized >= volatility_threshold else "low_volatility"


def _run_classical(
    prepared,
    *,
    train: pd.DataFrame,
    test: pd.DataFrame,
    split_id: str,
    cutoff_date: pd.Timestamp,
    train_size: int,
    market_regime: str,
) -> List[Dict[str, Any]]:
    rows = []
    signal_returns = split_signal_returns(test)
    for model_name, model in build_classical_models(prepared.y_train, random_state=RANDOM_STATE).items():
        start = time.perf_counter()
        model.fit(prepared.x_train_classical, prepared.y_train)
        train_seconds = time.perf_counter() - start
        infer_start = time.perf_counter()
        predictions = model.predict(prepared.x_test_classical)
        scores = model_scores(model, prepared.x_test_classical)
        infer_seconds = time.perf_counter() - infer_start
        metrics = evaluate_classifier(
            y_true=prepared.y_test,
            predictions=predictions,
            scores=scores,
            signal_returns=signal_returns,
        )
        rows.append(
            metric_row(
                model=model_name,
                model_family="classical",
                execution_mode="sklearn",
                train_size=train_size,
                feature_dim=None,
                split_id=split_id,
                cutoff_date=cutoff_date,
                metrics=metrics,
                train_seconds=train_seconds,
                infer_seconds=infer_seconds,
                market_regime=market_regime,
            )
        )
    return rows


def _run_quantum(
    prepared,
    *,
    test: pd.DataFrame,
    split_id: str,
    cutoff_date: pd.Timestamp,
    train_size: int,
    feature_dim: int,
    modes: list[str],
    market_regime: str,
) -> List[Dict[str, Any]]:
    rows = []
    signal_returns = split_signal_returns(test)
    kernel_bundle = compute_quantum_kernel_bundle(
        prepared.x_train_quantum,
        prepared.x_test_quantum,
        modes=modes,
        seed=RANDOM_STATE,
    )
    for mode in modes:
        kernel_train, kernel_test, resources, kernel_seconds = kernel_bundle[mode]
        model = SVC(kernel="precomputed", class_weight="balanced", probability=False)
        start = time.perf_counter()
        model.fit(kernel_train, prepared.y_train)
        train_seconds = kernel_seconds + (time.perf_counter() - start)
        infer_start = time.perf_counter()
        predictions = model.predict(kernel_test)
        raw_scores = model.decision_function(kernel_test)
        scores = 1.0 / (1.0 + np.exp(-raw_scores))
        infer_seconds = time.perf_counter() - infer_start
        metrics = evaluate_classifier(
            y_true=prepared.y_test,
            predictions=predictions,
            scores=scores,
            signal_returns=signal_returns,
        )
        rows.append(
            metric_row(
                model="quantum_kernel_svm",
                model_family="quantum",
                execution_mode=mode,
                train_size=train_size,
                feature_dim=feature_dim,
                split_id=split_id,
                cutoff_date=cutoff_date,
                metrics=metrics,
                train_seconds=train_seconds,
                infer_seconds=infer_seconds,
                qubits=resources.qubits,
                kernel_circuit_depth=resources.kernel_circuit_depth,
                kernel_two_qubit_gates=resources.kernel_two_qubit_gates,
                shots=resources.shots,
                selected_features=prepared.selected_features,
                market_regime=market_regime,
            )
        )
    return rows


def run_benchmark(config: Dict[str, Any], *, root: Path = PROJECT_ROOT) -> pd.DataFrame:
    dataset_path = project_path(config["dataset_path"], root=root)
    metrics_path = project_path(config["metrics_path"], root=root)
    resources_path = project_path(config["resources_path"], root=root)

    dataset = _filter_rows(read_dataset(dataset_path), config.get("tickers"))
    volatility_threshold = float(dataset["spy_vol_20d"].median())
    train_sizes = config.get("train_sizes", TRAIN_SIZES)
    feature_dims = config.get("feature_dims", FEATURE_DIMS)
    quantum_modes = config.get("quantum_modes", ["statevector_exact", "shots_1024", "noisy_1024"])
    cutoffs = config.get("cutoffs", DEFAULT_CUTOFFS)
    test_days = int(config.get("test_days", TEST_DAYS))
    run_classical = bool(config.get("run_classical", True))
    run_quantum = bool(config.get("run_quantum", True))

    rows: List[Dict[str, Any]] = []
    for train_size in train_sizes:
        bundles = make_walk_forward_splits(dataset, cutoffs=cutoffs, train_size=int(train_size), test_days=test_days)
        for bundle in bundles:
            regime = _market_regime(bundle.test, volatility_threshold)
            if run_classical:
                prepared = prepare_features(bundle.train, bundle.test, feature_dim=min(feature_dims))
                rows.extend(
                    _run_classical(
                        prepared,
                        train=bundle.train,
                        test=bundle.test,
                        split_id=bundle.split_id,
                        cutoff_date=bundle.cutoff_date,
                        train_size=int(train_size),
                        market_regime=regime,
                    )
                )
            if run_quantum:
                for feature_dim in feature_dims:
                    prepared = prepare_features(bundle.train, bundle.test, feature_dim=int(feature_dim))
                    rows.extend(
                        _run_quantum(
                            prepared,
                            test=bundle.test,
                            split_id=bundle.split_id,
                            cutoff_date=bundle.cutoff_date,
                            train_size=int(train_size),
                            feature_dim=int(feature_dim),
                            modes=quantum_modes,
                            market_regime=regime,
                        )
                    )

    metrics_df = pd.DataFrame(rows)
    _ensure_parent(metrics_path)
    metrics_df.to_csv(metrics_path, index=False)

    resource_columns = [
        "model",
        "execution_mode",
        "train_size",
        "feature_dim",
        "split_id",
        "cutoff_date",
        "qubits",
        "kernel_circuit_depth",
        "kernel_two_qubit_gates",
        "shots",
        "selected_features",
    ]
    resource_df = metrics_df[metrics_df["model_family"] == "quantum"][resource_columns].drop_duplicates()
    _ensure_parent(resources_path)
    resource_df.to_csv(resources_path, index=False)
    return metrics_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MarketMind-Q benchmark.")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "configs" / "sector_etf.yaml"))
    args = parser.parse_args()
    config = load_config(args.config)
    metrics_df = run_benchmark(config)
    print(json.dumps({"rows": len(metrics_df), "models": sorted(metrics_df["model"].unique().tolist())}, indent=2))


if __name__ == "__main__":
    main()
