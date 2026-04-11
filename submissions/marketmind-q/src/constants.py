"""Shared constants for the MarketMind-Q benchmark."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SECTOR_ETFS = [
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
]

BENCHMARK_TICKER = "SPY"
ALL_TICKERS = [*SECTOR_ETFS, BENCHMARK_TICKER]

FEATURE_COLUMNS = [
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

DEFAULT_CUTOFFS = [
    "2023-01-03",
    "2023-04-03",
    "2023-07-03",
    "2023-10-02",
    "2024-01-02",
    "2024-04-01",
    "2024-07-01",
    "2024-10-01",
    "2025-01-02",
    "2025-04-01",
    "2025-07-01",
    "2025-10-01",
]

TRAIN_SIZES = [40, 80, 160, 320]
FEATURE_DIMS = [2, 4]
TEST_DAYS = 20
FORWARD_DAYS = 5
EXCESS_RETURN_THRESHOLD = 0.0025
RANDOM_STATE = 42
TRADING_DAYS_PER_YEAR = 252

