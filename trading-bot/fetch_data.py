"""
fetch_data.py
=============
Get XAU/USD-style 1-minute OHLC data into the CSV format the backtester wants,
WITHOUT needing MetaTrader 5. Designed to run on a Chromebook's Linux container.

Output CSV columns:  time, open, high, low, close, tick_volume   (time in UTC)

Three sources
-------------
1. Synthetic (works offline, no internet — great for testing the pipeline now):
       python fetch_data.py --synthetic --days 5 --out data/xau_sample.csv

2. Yahoo Finance via yfinance (free, no account; uses gold FUTURES GC=F as a
   close proxy for spot XAUUSD — fine for pipeline/strategy testing, and limited
   by Yahoo to ~the last 7 days of 1m bars):
       pip install yfinance
       python fetch_data.py --yahoo --out data/gold_1m.csv

3. Convert a file you already exported (Dukascopy, or MT5 "Save as CSV", etc.):
       python fetch_data.py --convert raw.csv --out data/xau_1m.csv
   The converter auto-detects common column names (Date/Time/Gmt time/Open...).

For serious multi-month backtests, export real XAUUSD M1 from the MT5 terminal
(History Center / "Save as CSV") on any Windows machine, copy the file to your
Chromebook, and use --convert. See CHROMEBOOK.md.
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

OUT_COLS = ["time", "open", "high", "low", "close", "tick_volume"]


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------- #
# 1. Synthetic data (offline)                                                 #
# --------------------------------------------------------------------------- #
def make_synthetic(days: int, seed: int = 7, start_price: float = 2300.0) -> pd.DataFrame:
    """A realistic-ish 1m random walk with trend regimes, for pipeline testing."""
    n = days * 24 * 60
    rng = np.random.default_rng(seed)
    # Trend regimes via a slow sine + random walk; volatility ~ gold M1.
    drift = np.sin(np.linspace(0, days * 1.5, n)) * 6.0
    walk = rng.normal(0, 0.22, n).cumsum()
    close = start_price + drift + walk
    openp = close - rng.normal(0, 0.12, n)
    high = np.maximum(openp, close) + np.abs(rng.normal(0, 0.35, n))
    low = np.minimum(openp, close) - np.abs(rng.normal(0, 0.35, n))
    time = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({
        "time": time, "open": openp, "high": high, "low": low,
        "close": close, "tick_volume": rng.integers(50, 500, n),
    })


# --------------------------------------------------------------------------- #
# 2. Yahoo Finance (free, online)                                             #
# --------------------------------------------------------------------------- #
def fetch_yahoo(ticker: str = "GC=F", period: str = "7d") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        raise SystemExit("Install yfinance first:  pip install yfinance")

    df = yf.download(ticker, period=period, interval="1m",
                     progress=False, auto_adjust=False)
    if df is None or len(df) == 0:
        raise SystemExit("No data returned from Yahoo (rate-limited or offline?).")
    # yfinance may return a MultiIndex column set for a single ticker.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    tcol = "Datetime" if "Datetime" in df.columns else df.columns[0]
    out = pd.DataFrame({
        "time": pd.to_datetime(df[tcol], utc=True),
        "open": df["Open"], "high": df["High"],
        "low": df["Low"], "close": df["Close"],
        "tick_volume": df.get("Volume", 0),
    })
    return out.dropna().reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 3. Convert an exported CSV (Dukascopy / MT5 / generic)                       #
# --------------------------------------------------------------------------- #
_TIME_ALIASES = ["time", "date", "datetime", "gmt time", "timestamp", "local time"]
_OHLC_ALIASES = {
    "open": ["open", "o"],
    "high": ["high", "h"],
    "low": ["low", "l"],
    "close": ["close", "c", "close last"],
}


def convert_csv(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    cols = {c.lower().strip(): c for c in raw.columns}

    def find(aliases):
        for a in aliases:
            if a in cols:
                return cols[a]
        return None

    tcol = find(_TIME_ALIASES)
    if tcol is None:
        raise SystemExit(f"Could not find a time column in {path}. "
                         f"Columns were: {list(raw.columns)}")

    out = pd.DataFrame()
    # Dukascopy uses 'dd.mm.yyyy HH:MM:SS.000'; let pandas infer, force UTC.
    out["time"] = pd.to_datetime(raw[tcol], utc=True, errors="coerce",
                                 dayfirst=True)
    for std, aliases in _OHLC_ALIASES.items():
        col = find(aliases)
        if col is None:
            raise SystemExit(f"Missing '{std}' column in {path}.")
        out[std] = pd.to_numeric(raw[col], errors="coerce")
    vcol = find(["tick_volume", "volume", "vol"])
    out["tick_volume"] = pd.to_numeric(raw[vcol], errors="coerce") if vcol else 0
    out = out.dropna(subset=["time", "open", "high", "low", "close"])
    return out.sort_values("time").reset_index(drop=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch/convert 1m data for the backtester")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--synthetic", action="store_true", help="Generate offline test data.")
    src.add_argument("--yahoo", action="store_true", help="Download from Yahoo Finance.")
    src.add_argument("--convert", metavar="FILE", help="Convert an exported CSV.")
    p.add_argument("--days", type=int, default=5, help="Days of synthetic data.")
    p.add_argument("--ticker", default="GC=F", help="Yahoo ticker (default gold futures).")
    p.add_argument("--period", default="7d", help="Yahoo lookback (max ~7d for 1m).")
    p.add_argument("--out", default="data/xau_1m.csv", help="Output CSV path.")
    args = p.parse_args()

    if args.synthetic:
        df = make_synthetic(args.days)
    elif args.yahoo:
        df = fetch_yahoo(args.ticker, args.period)
    else:
        df = convert_csv(args.convert)

    _ensure_dir(args.out)
    df[OUT_COLS].to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out} "
          f"({df['time'].min()} -> {df['time'].max()})")


if __name__ == "__main__":
    main()
