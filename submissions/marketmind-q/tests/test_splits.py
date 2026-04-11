from __future__ import annotations

import numpy as np
import pandas as pd

from src.constants import FEATURE_COLUMNS
from src.splits import class_balanced_recent_sample, make_walk_forward_splits, prepare_features


def _dataset(rows=160):
    dates = pd.bdate_range("2022-01-03", periods=rows)
    records = []
    for idx, date in enumerate(dates):
        target = idx % 2
        records.append(
            {
                "date": date,
                "ticker": "XLF" if idx % 3 else "XLK",
                "close": 100 + idx,
                "volume": 1000,
                "target": target,
                "excess_return_5d": 0.01 if target else -0.01,
                **{column: float(idx + offset) for offset, column in enumerate(FEATURE_COLUMNS)},
            }
        )
    return pd.DataFrame(records)


def test_class_balanced_recent_sample_returns_requested_size_and_balance():
    data = _dataset()
    sample = class_balanced_recent_sample(data, train_size=40)
    assert len(sample) == 40
    assert sample["target"].value_counts().to_dict() == {0: 20, 1: 20}
    assert sample["date"].max() == data["date"].max()


def test_walk_forward_split_keeps_training_before_cutoff():
    data = _dataset()
    cutoff = "2022-05-02"
    splits = make_walk_forward_splits(data, cutoffs=[cutoff], train_size=40, test_days=10)
    assert len(splits) == 1
    split = splits[0]
    assert split.train["date"].max() < pd.Timestamp(cutoff)
    assert split.test["date"].min() >= pd.Timestamp(cutoff)


def test_prepare_features_fits_train_only_and_clips_quantum_angles():
    data = _dataset()
    train = data.iloc[:80].copy()
    test = data.iloc[80:100].copy()
    test.loc[:, FEATURE_COLUMNS] = 1_000_000.0
    prepared = prepare_features(train, test, feature_dim=2)
    assert prepared.x_train_classical.shape == (80, len(FEATURE_COLUMNS))
    assert prepared.x_train_quantum.shape == (80, 2)
    assert prepared.x_test_quantum.shape == (20, 2)
    assert np.all(prepared.x_test_quantum >= 0.0)
    assert np.all(prepared.x_test_quantum <= np.pi)

