from __future__ import annotations

import pandas as pd

from src.constants import FEATURE_COLUMNS
from src.run_benchmark import run_benchmark


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
    frame = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def test_classical_benchmark_smoke(tmp_path):
    dataset_path = tmp_path / "data" / "dataset.csv"
    _frozen_dataset(dataset_path)
    config = {
        "dataset_path": str(dataset_path),
        "metrics_path": str(tmp_path / "results" / "metrics.csv"),
        "resources_path": str(tmp_path / "results" / "resources.csv"),
        "tickers": ["XLF", "XLK"],
        "train_sizes": [40],
        "feature_dims": [2],
        "test_days": 10,
        "cutoffs": ["2022-06-01"],
        "quantum_modes": ["statevector_exact"],
        "run_classical": True,
        "run_quantum": False,
    }
    metrics = run_benchmark(config, root=tmp_path)
    assert not metrics.empty
    assert set(metrics["model_family"]) == {"classical"}
    assert (tmp_path / "results" / "metrics.csv").exists()

