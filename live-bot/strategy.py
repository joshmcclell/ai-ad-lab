"""
strategy.py
===========
MEAN REVERSION SCALPING for XAU/USD, 1-minute. Fully rule-based, no ML.

Idea: trade WITH the EMA trend, but only on a PULLBACK into the EMA zone that
then bounces/rejects - buying dips in an uptrend, selling rallies in a
downtrend. Stop and target are both 1.0 x ATR (1:1).

Entry rules (evaluated on the last CLOSED 1-minute candle):

  LONG  (uptrend, buy the dip):
    - EMA20 > EMA50                      (uptrend bias)
    - candle pulled back to the EMA zone (low <= EMA20) but CLOSED back above it
    - RSI(7) between 35 and 48           (a correction, not oversold)
    - bullish close, no large lower wick (clean bounce)
    - ATR(5) >= atr_min                  (enough movement)

  SHORT (downtrend, sell the rally):
    - EMA20 < EMA50                      (downtrend bias)
    - candle rallied to the EMA zone (high >= EMA20) but CLOSED back below it
    - RSI(7) between 52 and 65           (a correction, not overbought)
    - bearish close, no large upper wick
    - ATR(5) >= atr_min

Time filter (London session) and the news blackout are applied live. The
spread filter (<= max_spread_points) is enforced in bot.py because it needs the
live bid/ask. The same evaluate() drives both the live bot and the backtester.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import pandas as pd


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


@dataclass
class Signal:
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    atr: float
    reason: str

    @property
    def is_trade(self) -> bool:
        return self.direction in (Direction.LONG, Direction.SHORT)


# --------------------------------------------------------------------------- #
# Time / session helpers                                                       #
# --------------------------------------------------------------------------- #
def in_session(now_local: datetime, session_cfg) -> bool:
    t = now_local.time()
    return session_cfg.session_start <= t <= session_cfg.session_end


def in_news_blackout(now_local: datetime, session_cfg) -> bool:
    buffer = timedelta(minutes=session_cfg.news_buffer_minutes)
    for event in session_cfg.news_events:
        ev = event
        if ev.tzinfo is None:
            ev = ev.replace(tzinfo=now_local.tzinfo)
        if ev - buffer <= now_local <= ev + buffer:
            return True
    return False


# --------------------------------------------------------------------------- #
# Signal generator                                                             #
# --------------------------------------------------------------------------- #
def evaluate(
    df: pd.DataFrame,
    strategy_cfg,
    session_cfg=None,
    now_local: Optional[datetime] = None,
    check_time: bool = True,
) -> Signal:
    """Evaluate the most recent closed candle (last row of `df`)."""
    min_bars = max(strategy_cfg.ema_slow_period, strategy_cfg.atr_period) + 2
    if len(df) < min_bars:
        return Signal(Direction.NONE, 0, 0, 0, 0, "not enough history")

    i = len(df) - 1
    row = df.iloc[i]
    price = float(row["close"])
    o, h, l, c = (float(row["open"]), float(row["high"]),
                  float(row["low"]), float(row["close"]))
    ema_fast = float(row["ema_fast"])
    ema_slow = float(row["ema_slow"])
    rsi_val = float(row["rsi"])
    atr_val = float(row["atr"])

    if any(pd.isna(v) for v in (ema_fast, ema_slow, rsi_val, atr_val)):
        return Signal(Direction.NONE, price, 0, 0, 0, "indicators warming up")

    # --- Time / session filter (live only) ---------------------------------
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

    # 1:1 -> stop and target are the same distance from entry.
    sl_dist = strategy_cfg.sl_atr_multiplier * atr_val
    tp_dist = sl_dist * strategy_cfg.risk_reward_ratio

    # Candle anatomy.
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    max_wick = strategy_cfg.max_wick_to_body * body if body > 0 else 0.0

    # --- LONG: uptrend, pullback to EMA zone, bounce -----------------------
    uptrend = ema_fast > ema_slow
    pulled_back_long = (l <= ema_fast) and (c > ema_fast)   # tested zone, closed above
    rsi_long = strategy_cfg.rsi_long_min <= rsi_val <= strategy_cfg.rsi_long_max
    bull_candle = (c > o) and (lower_wick <= max_wick)      # clean bullish, no big lower wick

    if uptrend and pulled_back_long and rsi_long and bull_candle:
        return Signal(
            direction=Direction.LONG,
            entry=price,
            stop_loss=price - sl_dist,
            take_profit=price + tp_dist,
            atr=atr_val,
            reason=(f"LONG MR: EMA20>EMA50, pullback to EMA, RSI={rsi_val:.1f}, "
                    f"ATR={atr_val:.3f}, bullish close"),
        )

    # --- SHORT: downtrend, pullback to EMA zone, reject --------------------
    downtrend = ema_fast < ema_slow
    pulled_back_short = (h >= ema_fast) and (c < ema_fast)  # tested zone, closed below
    rsi_short = strategy_cfg.rsi_short_min <= rsi_val <= strategy_cfg.rsi_short_max
    bear_candle = (c < o) and (upper_wick <= max_wick)      # clean bearish, no big upper wick

    if downtrend and pulled_back_short and rsi_short and bear_candle:
        return Signal(
            direction=Direction.SHORT,
            entry=price,
            stop_loss=price + sl_dist,
            take_profit=price - tp_dist,
            atr=atr_val,
            reason=(f"SHORT MR: EMA20<EMA50, rally to EMA, RSI={rsi_val:.1f}, "
                    f"ATR={atr_val:.3f}, bearish close"),
        )

    return Signal(Direction.NONE, price, 0, 0, atr_val, "no setup")
