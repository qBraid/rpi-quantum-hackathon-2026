"""Dataset and feature construction for MarketMind-Q."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable

import numpy as np
import pandas as pd

from .constants import (
    BENCHMARK_TICKER,
    EXCESS_RETURN_THRESHOLD,
    FEATURE_COLUMNS,
    FORWARD_DAYS,
    SECTOR_ETFS,
)


def standardize_price_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Normalize yfinance output into a stable OHLCV frame."""
    if raw is None or raw.empty:
        raise ValueError(f"No price data for {ticker}.")
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [col[0] for col in frame.columns]
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    frame = frame.sort_index()
    rename_map = {col: col.title() for col in frame.columns}
    frame = frame.rename(columns=rename_map)
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [col for col in required if col not in frame.columns]
    if missing:
        raise ValueError(f"{ticker} missing columns: {missing}")
    frame = frame[required].copy()
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["Close"] = frame["Close"].ffill().bfill()
    frame["Volume"] = frame["Volume"].replace(0, np.nan).ffill().bfill().fillna(1.0)
    frame = frame.dropna(subset=["Close"])
    frame["Ticker"] = str(ticker).upper()
    return frame


def build_feature_dataset(
    price_frames: Dict[str, pd.DataFrame],
    *,
    sector_tickers: Iterable[str] = SECTOR_ETFS,
    benchmark_ticker: str = BENCHMARK_TICKER,
    forward_days: int = FORWARD_DAYS,
    threshold: float = EXCESS_RETURN_THRESHOLD,
) -> pd.DataFrame:
    """Build the frozen finance classification dataset from OHLCV frames."""
    if benchmark_ticker not in price_frames:
        raise ValueError(f"Benchmark ticker {benchmark_ticker} is required.")

    standardized = {
        ticker: standardize_price_frame(frame, ticker)
        for ticker, frame in price_frames.items()
        if frame is not None and not frame.empty
    }
    spy = standardized[benchmark_ticker][["Close"]].rename(columns={"Close": "spy_close"})
    spy["spy_forward_return_5d"] = spy["spy_close"].shift(-forward_days) / spy["spy_close"] - 1.0
    spy["spy_vol_20d"] = spy["spy_close"].pct_change().rolling(20, min_periods=10).std()

    rows = []
    for ticker in sector_tickers:
        if ticker not in standardized:
            continue
        frame = standardized[ticker].join(spy, how="inner")
        close = frame["Close"]
        volume = frame["Volume"].replace(0, np.nan)

        frame["ret_1d"] = close.pct_change(1)
        frame["ret_5d"] = close.pct_change(5)
        frame["ret_20d"] = close.pct_change(20)
        daily_ret = close.pct_change()
        frame["vol_5d"] = daily_ret.rolling(5, min_periods=3).std()
        frame["vol_20d"] = daily_ret.rolling(20, min_periods=10).std()
        frame["volume_ratio_5d"] = volume / volume.rolling(5, min_periods=3).mean()
        frame["volume_ratio_20d"] = volume / volume.rolling(20, min_periods=10).mean()
        etf_ret_20 = close.pct_change(20)
        spy_ret_20 = frame["spy_close"].pct_change(20)
        frame["relative_strength_20d"] = etf_ret_20 - spy_ret_20
        frame["forward_return_5d"] = close.shift(-forward_days) / close - 1.0
        frame["excess_return_5d"] = frame["forward_return_5d"] - frame["spy_forward_return_5d"]
        frame["target"] = (frame["excess_return_5d"] > threshold).astype(int)

        dates = pd.Series(frame.index, index=frame.index)
        weekday_angle = 2.0 * math.pi * dates.dt.weekday / 5.0
        month_angle = 2.0 * math.pi * (dates.dt.month - 1) / 12.0
        frame["weekday_sin"] = np.sin(weekday_angle)
        frame["weekday_cos"] = np.cos(weekday_angle)
        frame["month_sin"] = np.sin(month_angle)
        frame["month_cos"] = np.cos(month_angle)
        frame["ticker"] = ticker
        frame["date"] = frame.index
        rows.append(frame)

    if not rows:
        raise ValueError("No sector ETF rows could be built.")

    dataset = pd.concat(rows, axis=0, ignore_index=True)
    required = ["date", "ticker", "Close", "Volume", *FEATURE_COLUMNS, "forward_return_5d", "spy_forward_return_5d", "excess_return_5d", "target"]
    dataset = dataset[required].rename(columns={"Close": "close", "Volume": "volume"})
    dataset = dataset.replace([np.inf, -np.inf], np.nan)
    dataset = dataset.dropna(subset=[*FEATURE_COLUMNS, "forward_return_5d", "spy_forward_return_5d", "excess_return_5d", "target"])
    dataset["date"] = pd.to_datetime(dataset["date"])
    dataset["target"] = dataset["target"].astype(int)
    return dataset.sort_values(["date", "ticker"]).reset_index(drop=True)


def write_dataset(dataset: pd.DataFrame, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frozen = dataset.copy()
    frozen["date"] = pd.to_datetime(frozen["date"]).dt.strftime("%Y-%m-%d")
    frozen.to_csv(output_path, index=False)
    return output_path


def read_dataset(path: str | Path) -> pd.DataFrame:
    dataset = pd.read_csv(path)
    dataset["date"] = pd.to_datetime(dataset["date"])
    dataset["target"] = dataset["target"].astype(int)
    return dataset

