"""
strategy.py
===========
The rule-based decision engine. Given a DataFrame of recent 1-minute candles
(with indicators attached) it returns a Signal describing whether to go long,
short, or stand aside, plus the stop-loss / take-profit prices.

All rules are explicit and transparent - there is no machine learning here.
The same function is used by both the live bot and the backtester so the
two can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import pandas as pd

from indicators import bearish_confirmation, bullish_confirmation


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


@dataclass
class Signal:
    direction: Direction
    entry: float            # reference entry price (signal candle close)
    stop_loss: float
    take_profit: float
    atr: float
    reason: str             # human-readable explanation / rejection reason

    @property
    def is_trade(self) -> bool:
        return self.direction in (Direction.LONG, Direction.SHORT)


# --------------------------------------------------------------------------- #
# Time / session helpers                                                       #
# --------------------------------------------------------------------------- #
def in_session(now_local: datetime, session_cfg) -> bool:
    """True if `now_local` (tz-aware, broker/local tz) is inside the window."""
    t = now_local.time()
    return session_cfg.session_start <= t <= session_cfg.session_end


def in_news_blackout(now_local: datetime, session_cfg) -> bool:
    """True if we are within +/- buffer of any configured news event."""
    buffer = timedelta(minutes=session_cfg.news_buffer_minutes)
    for event in session_cfg.news_events:
        ev = event
        # Normalise naive datetimes to the session timezone for comparison.
        if ev.tzinfo is None:
            ev = ev.replace(tzinfo=now_local.tzinfo)
        if ev - buffer <= now_local <= ev + buffer:
            return True
    return False


# --------------------------------------------------------------------------- #
# The signal generator                                                         #
# --------------------------------------------------------------------------- #
def evaluate(
    df: pd.DataFrame,
    strategy_cfg,
    session_cfg=None,
    now_local: Optional[datetime] = None,
    check_time: bool = True,
) -> Signal:
    """
    Evaluate the most recent *closed* candle (the last row of `df`).

    `df` must already contain the indicator columns produced by
    indicators.add_indicators(): ema_fast, ema_slow, rsi, atr.
    """
    # Need enough history for the slow EMA and ATR to be valid.
    min_bars = max(strategy_cfg.ema_slow_period, strategy_cfg.atr_period) + 2
    if len(df) < min_bars:
        return Signal(Direction.NONE, 0, 0, 0, 0, "not enough history")

    i = len(df) - 1                      # index of the last closed candle
    row = df.iloc[i]
    price = float(row["close"])
    ema_fast = float(row["ema_fast"])
    ema_slow = float(row["ema_slow"])
    rsi_val = float(row["rsi"])
    atr_val = float(row["atr"])

    # Any NaN means the indicators have not warmed up yet.
    if any(pd.isna(v) for v in (ema_fast, ema_slow, rsi_val, atr_val)):
        return Signal(Direction.NONE, price, 0, 0, 0, "indicators warming up")

    # --- Time / session filter (optional; skipped by the backtester) -------
    if check_time and session_cfg is not None and now_local is not None:
        if getattr(session_cfg, "enforce_session", True) \
                and not in_session(now_local, session_cfg):
            return Signal(Direction.NONE, price, 0, 0, atr_val, "outside session")
        if in_news_blackout(now_local, session_cfg):
            return Signal(Direction.NONE, price, 0, 0, atr_val, "news blackout")

    # --- Volatility filter -------------------------------------------------
    if atr_val < strategy_cfg.atr_min:
        return Signal(Direction.NONE, price, 0, 0, atr_val,
                      f"ATR {atr_val:.3f} < min {strategy_cfg.atr_min}")

    sl_dist = strategy_cfg.sl_atr_multiplier * atr_val
    tp_dist = sl_dist * strategy_cfg.risk_reward_ratio

    # --- LONG setup --------------------------------------------------------
    long_trend = (ema_fast > ema_slow) and (price > ema_fast) and (price > ema_slow)
    long_rsi = strategy_cfg.rsi_long_min < rsi_val < strategy_cfg.rsi_long_max
    long_candle = (not strategy_cfg.require_candle_confirmation
                   or bullish_confirmation(df, i))

    if long_trend and long_rsi and long_candle:
        return Signal(
            direction=Direction.LONG,
            entry=price,
            stop_loss=price - sl_dist,
            take_profit=price + tp_dist,
            atr=atr_val,
            reason=(f"LONG: 20EMA>50EMA, close>EMAs, RSI={rsi_val:.1f}, "
                    f"ATR={atr_val:.3f}, candle ok"),
        )

    # --- SHORT setup -------------------------------------------------------
    short_trend = (ema_fast < ema_slow) and (price < ema_fast) and (price < ema_slow)
    short_rsi = strategy_cfg.rsi_short_min < rsi_val < strategy_cfg.rsi_short_max
    short_candle = (not strategy_cfg.require_candle_confirmation
                    or bearish_confirmation(df, i))

    if short_trend and short_rsi and short_candle:
        return Signal(
            direction=Direction.SHORT,
            entry=price,
            stop_loss=price + sl_dist,
            take_profit=price - tp_dist,
            atr=atr_val,
            reason=(f"SHORT: 20EMA<50EMA, close<EMAs, RSI={rsi_val:.1f}, "
                    f"ATR={atr_val:.3f}, candle ok"),
        )

    return Signal(Direction.NONE, price, 0, 0, atr_val, "no setup")
