"""
indicators.py
=============
All technical indicators and candle-pattern checks used by the strategy.

The maths is kept fully transparent (no black boxes). We use `pandas-ta` for
the standard indicators where available and fall back to clean, well-documented
manual implementations otherwise - so the bot still works if pandas-ta cannot
be installed in your environment.

Every function takes a pandas DataFrame with the columns:
    open, high, low, close   (and optionally tick_volume)
indexed/ordered oldest -> newest, and returns a pandas Series aligned to it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import pandas_ta as pta  # noqa: F401
    _HAS_PANDAS_TA = True
except Exception:  # pragma: no cover - pandas_ta optional
    _HAS_PANDAS_TA = False


# --------------------------------------------------------------------------- #
# Core indicators                                                             #
# --------------------------------------------------------------------------- #
def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    if _HAS_PANDAS_TA:
        return pta.ema(series, length=period)
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    if _HAS_PANDAS_TA:
        return pta.rsi(series, length=period)

    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    # Wilder's smoothing == EMA with alpha = 1/period.
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 the RSI is, by definition, 100.
    out = out.where(avg_loss != 0.0, 100.0)
    return out


def atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Average True Range (Wilder), expressed in price units (USD for gold)."""
    if _HAS_PANDAS_TA:
        return pta.atr(df["high"], df["low"], df["close"], length=period)

    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / period, adjust=False).mean()


# --------------------------------------------------------------------------- #
# Candle-pattern confirmation                                                 #
# --------------------------------------------------------------------------- #
def is_bullish_engulfing(df: pd.DataFrame, i: int) -> bool:
    """Bar `i` is a bullish engulfing of bar `i-1`."""
    if i < 1:
        return False
    o0, c0 = df["open"].iloc[i - 1], df["close"].iloc[i - 1]
    o1, c1 = df["open"].iloc[i], df["close"].iloc[i]
    prev_bearish = c0 < o0
    curr_bullish = c1 > o1
    engulfs = (c1 >= o0) and (o1 <= c0)
    return bool(prev_bearish and curr_bullish and engulfs)


def is_bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    """Bar `i` is a bearish engulfing of bar `i-1`."""
    if i < 1:
        return False
    o0, c0 = df["open"].iloc[i - 1], df["close"].iloc[i - 1]
    o1, c1 = df["open"].iloc[i], df["close"].iloc[i]
    prev_bullish = c0 > o0
    curr_bearish = c1 < o1
    engulfs = (c1 <= o0) and (o1 >= c0)
    return bool(prev_bullish and curr_bearish and engulfs)


def is_bullish_pin_bar(df: pd.DataFrame, i: int, wick_ratio: float = 2.0) -> bool:
    """Long lower wick, small body near the top (rejection of lower prices)."""
    o, h, l, c = (df["open"].iloc[i], df["high"].iloc[i],
                  df["low"].iloc[i], df["close"].iloc[i])
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    return bool(lower_wick >= wick_ratio * body and lower_wick > upper_wick
                and c >= o)


def is_bearish_pin_bar(df: pd.DataFrame, i: int, wick_ratio: float = 2.0) -> bool:
    """Long upper wick, small body near the bottom (rejection of higher prices)."""
    o, h, l, c = (df["open"].iloc[i], df["high"].iloc[i],
                  df["low"].iloc[i], df["close"].iloc[i])
    rng = h - l
    if rng <= 0:
        return False
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    return bool(upper_wick >= wick_ratio * body and upper_wick > lower_wick
                and c <= o)


def bullish_confirmation(df: pd.DataFrame, i: int) -> bool:
    return is_bullish_engulfing(df, i) or is_bullish_pin_bar(df, i)


def bearish_confirmation(df: pd.DataFrame, i: int) -> bool:
    return is_bearish_engulfing(df, i) or is_bearish_pin_bar(df, i)


# --------------------------------------------------------------------------- #
# Convenience: attach all indicator columns to a DataFrame                     #
# --------------------------------------------------------------------------- #
def add_indicators(df: pd.DataFrame, strategy_cfg) -> pd.DataFrame:
    """Return a copy of `df` with ema_fast, ema_slow, rsi and atr columns."""
    out = df.copy()
    out["ema_fast"] = ema(out["close"], strategy_cfg.ema_fast_period)
    out["ema_slow"] = ema(out["close"], strategy_cfg.ema_slow_period)
    out["rsi"] = rsi(out["close"], strategy_cfg.rsi_period)
    out["atr"] = atr(out, strategy_cfg.atr_period)
    return out
