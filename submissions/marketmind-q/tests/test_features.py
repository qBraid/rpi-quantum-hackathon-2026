from __future__ import annotations

import numpy as np
import pandas as pd

from src.features import build_feature_dataset


def _prices(close_values, *, volume=1000):
    index = pd.bdate_range("2022-01-03", periods=len(close_values))
    close = np.asarray(close_values, dtype=float)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.01,
            "Low": close * 0.99,
            "Close": close,
            "Volume": np.full(len(close), volume, dtype=float),
        },
        index=index,
    )


def test_target_uses_forward_five_day_excess_return():
    spy = _prices(np.linspace(100, 140, 80))
    xlf = _prices(np.linspace(50, 100, 80))
    dataset = build_feature_dataset({"SPY": spy, "XLF": xlf}, sector_tickers=["XLF"])
    row = dataset.iloc[5]
    prices = xlf.loc[pd.Timestamp(row["date"]):]
    spy_prices = spy.loc[pd.Timestamp(row["date"]):]
    expected_forward = prices["Close"].iloc[5] / prices["Close"].iloc[0] - 1.0
    expected_spy = spy_prices["Close"].iloc[5] / spy_prices["Close"].iloc[0] - 1.0
    assert np.isclose(row["forward_return_5d"], expected_forward)
    assert np.isclose(row["spy_forward_return_5d"], expected_spy)
    assert row["target"] == int((expected_forward - expected_spy) > 0.0025)


def test_features_for_a_date_do_not_change_when_future_prices_change():
    spy = _prices(np.linspace(100, 140, 90))
    xlf = _prices(np.linspace(50, 100, 90))
    baseline = build_feature_dataset({"SPY": spy, "XLF": xlf}, sector_tickers=["XLF"])
    target_date = baseline["date"].iloc[10]

    changed_xlf = xlf.copy()
    future_index = changed_xlf.index.get_loc(pd.Timestamp(target_date)) + 5
    changed_xlf.iloc[future_index, changed_xlf.columns.get_loc("Close")] *= 1.5
    changed = build_feature_dataset({"SPY": spy, "XLF": changed_xlf}, sector_tickers=["XLF"])

    base_row = baseline[baseline["date"] == target_date].iloc[0]
    changed_row = changed[changed["date"] == target_date].iloc[0]
    feature_columns = [
        "ret_1d",
        "ret_5d",
        "ret_20d",
        "vol_5d",
        "vol_20d",
        "volume_ratio_5d",
        "volume_ratio_20d",
        "relative_strength_20d",
        "spy_vol_20d",
        "weekday_sin",
        "weekday_cos",
        "month_sin",
        "month_cos",
    ]
    assert np.allclose(base_row[feature_columns].astype(float), changed_row[feature_columns].astype(float))
    assert base_row["forward_return_5d"] != changed_row["forward_return_5d"]
