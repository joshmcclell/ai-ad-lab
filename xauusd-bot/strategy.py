"""Trading strategy: trend filter + RSI cross entries, ATR/swing stops, RR target.

Strategy summary (all thresholds configurable in .env):

  Trend filter
    - Longs allowed only when SMA_FAST > SMA_SLOW (bullish).
    - Shorts allowed only when SMA_FAST < SMA_SLOW (bearish).

  Entry
    - Long  : bullish trend AND RSI crosses UP through RSI_OVERSOLD (default 30).
    - Short : bearish trend AND RSI crosses DOWN through RSI_OVERBOUGHT (default 70).

  Stops / targets
    - Stop loss: ATR-based (entry -/+ ATR_MULTIPLIER*ATR) or recent swing low/high.
    - Take profit: RISK_REWARD * stop distance.

The bot acts on CLOSED candles only — the caller passes a frame whose last row is
the most recently completed bar.

NOTE on the included ICT transcript: that commentary (fair value gaps, volume
imbalances, consequent encroachment, liquidity runs) is a discretionary, visual
method. It does not translate into the mechanical, backtestable rules requested in
the spec, so it is intentionally NOT encoded here. The SMA/RSI/ATR model below is
the precise, testable strategy. Treat the transcript as background context only.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import CONFIG
from indicators import recent_swing_high, recent_swing_low

LONG = "long"
SHORT = "short"


@dataclass
class Signal:
    side: str | None            # "long", "short", or None
    entry: float                # reference price (last close)
    stop_loss: float
    take_profit: float
    atr: float
    reason: str

    @property
    def has_trade(self) -> bool:
        return self.side in (LONG, SHORT)


def _crossed_up(prev: float, now: float, level: float) -> bool:
    return prev <= level < now


def _crossed_down(prev: float, now: float, level: float) -> bool:
    return prev >= level > now


def evaluate(df: pd.DataFrame) -> Signal:
    """Evaluate the strategy on the last closed bar of an indicator-enriched frame."""
    if len(df) < 2:
        return Signal(None, 0, 0, 0, 0, "not enough bars")

    cur = df.iloc[-1]
    prev = df.iloc[-2]

    # Guard against warm-up NaNs (early bars before the slow SMA is defined).
    required = [cur["sma_fast"], cur["sma_slow"], cur["rsi"], prev["rsi"], cur["atr"]]
    if any(pd.isna(v) for v in required):
        return Signal(None, float(cur["close"]), 0, 0, 0, "indicators warming up")

    entry = float(cur["close"])
    atr = float(cur["atr"])
    bullish = cur["sma_fast"] > cur["sma_slow"]
    bearish = cur["sma_fast"] < cur["sma_slow"]

    # --- Long setup ---
    if bullish and _crossed_up(float(prev["rsi"]), float(cur["rsi"]), CONFIG.rsi_oversold):
        sl = _stop_for_long(df, entry, atr)
        if sl >= entry:
            return Signal(None, entry, 0, 0, atr, "long rejected: stop not below entry")
        tp = entry + CONFIG.risk_reward * (entry - sl)
        return Signal(
            LONG, entry, sl, tp, atr,
            f"LONG: SMA{CONFIG.sma_fast}>{CONFIG.sma_slow} & RSI crossed up {CONFIG.rsi_oversold} "
            f"({prev['rsi']:.1f}->{cur['rsi']:.1f})",
        )

    # --- Short setup ---
    if bearish and _crossed_down(float(prev["rsi"]), float(cur["rsi"]), CONFIG.rsi_overbought):
        sl = _stop_for_short(df, entry, atr)
        if sl <= entry:
            return Signal(None, entry, 0, 0, atr, "short rejected: stop not above entry")
        tp = entry - CONFIG.risk_reward * (sl - entry)
        return Signal(
            SHORT, entry, sl, tp, atr,
            f"SHORT: SMA{CONFIG.sma_fast}<{CONFIG.sma_slow} & RSI crossed down {CONFIG.rsi_overbought} "
            f"({prev['rsi']:.1f}->{cur['rsi']:.1f})",
        )

    trend = "bullish" if bullish else "bearish" if bearish else "flat"
    return Signal(None, entry, 0, 0, atr, f"no entry (trend={trend}, rsi={cur['rsi']:.1f})")


def _stop_for_long(df: pd.DataFrame, entry: float, atr: float) -> float:
    if CONFIG.sl_method == "swing":
        return recent_swing_low(df, CONFIG.swing_lookback)
    return entry - CONFIG.atr_multiplier * atr


def _stop_for_short(df: pd.DataFrame, entry: float, atr: float) -> float:
    if CONFIG.sl_method == "swing":
        return recent_swing_high(df, CONFIG.swing_lookback)
    return entry + CONFIG.atr_multiplier * atr
