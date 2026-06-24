"""Indicator calculations — all in one place so the strategy stays readable.

Everything is computed with the `ta` library on a pandas DataFrame that already
has the columns: time, open, high, low, close, tick_volume.

To add or tweak an indicator, edit ONLY this file.
"""
from __future__ import annotations

import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
from ta.volatility import AverageTrueRange

from config import CONFIG


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with sma_fast, sma_slow, rsi and atr columns added."""
    out = df.copy()

    out["sma_fast"] = SMAIndicator(
        close=out["close"], window=CONFIG.sma_fast, fillna=False
    ).sma_indicator()

    out["sma_slow"] = SMAIndicator(
        close=out["close"], window=CONFIG.sma_slow, fillna=False
    ).sma_indicator()

    out["rsi"] = RSIIndicator(
        close=out["close"], window=CONFIG.rsi_period, fillna=False
    ).rsi()

    out["atr"] = AverageTrueRange(
        high=out["high"],
        low=out["low"],
        close=out["close"],
        window=CONFIG.atr_period,
        fillna=False,
    ).average_true_range()

    return out


def recent_swing_low(df: pd.DataFrame, lookback: int, before_index: int | None = None) -> float:
    """Lowest low over the last `lookback` *closed* bars (excluding the current one)."""
    end = len(df) - 1 if before_index is None else before_index
    start = max(0, end - lookback)
    window = df["low"].iloc[start:end]
    return float(window.min()) if len(window) else float(df["low"].iloc[end])


def recent_swing_high(df: pd.DataFrame, lookback: int, before_index: int | None = None) -> float:
    """Highest high over the last `lookback` *closed* bars (excluding the current one)."""
    end = len(df) - 1 if before_index is None else before_index
    start = max(0, end - lookback)
    window = df["high"].iloc[start:end]
    return float(window.max()) if len(window) else float(df["high"].iloc[end])
