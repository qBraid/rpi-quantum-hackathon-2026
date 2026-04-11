"""CLI to build the frozen MarketMind-Q dataset."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import pandas as pd
import yfinance as yf

from .constants import ALL_TICKERS, PROJECT_ROOT, SECTOR_ETFS
from .features import build_feature_dataset, write_dataset


def download_prices(tickers: list[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    prices: Dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        print(f"Downloading {ticker}...")
        frame = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if frame is None or frame.empty:
            raise RuntimeError(f"No yfinance rows returned for {ticker}.")
        prices[ticker] = frame
    return prices


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the frozen MarketMind-Q finance dataset.")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2026-03-31")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "data" / "marketmind_qml_dataset.csv"))
    args = parser.parse_args()

    price_frames = download_prices(ALL_TICKERS, args.start, args.end)
    dataset = build_feature_dataset(price_frames, sector_tickers=SECTOR_ETFS)
    output_path = write_dataset(dataset, Path(args.output))
    print(f"Wrote {len(dataset):,} rows to {output_path}")
    print(dataset.groupby("target").size().rename("rows").to_string())


if __name__ == "__main__":
    main()

