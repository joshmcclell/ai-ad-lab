"""
strategy.py
===========
The rule-based decision engine for the NEW bot.

>>> THIS IS A CLEAN SLATE. The entry/exit rules are intentionally empty until
>>> you provide your strategy. Right now evaluate() returns NONE (no trade) so
>>> the rest of the bot - connection, sizing, alerts, logging - can be wired up
>>> and tested safely without taking any positions.

When you paste your strategy, the rules go inside evaluate(): compute the
indicators you need (add helpers to indicators.py), check your entry
conditions, and return a Signal with entry / stop_loss / take_profit. The same
evaluate() is used by both the live bot and the backtester, so they can never
drift apart.
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
# Time / session helpers (kept ready for your strategy's time rules)          #
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
# The signal generator  --  AWAITING YOUR STRATEGY RULES                       #
# --------------------------------------------------------------------------- #
def evaluate(
    df: pd.DataFrame,
    strategy_cfg,
    session_cfg=None,
    now_local: Optional[datetime] = None,
    check_time: bool = True,
) -> Signal:
    """
    Evaluate the most recent closed candle (last row of `df`) and decide
    whether to go LONG, SHORT, or stand aside.

    PLACEHOLDER: returns NONE until your strategy rules are added here.
    """
    price = float(df["close"].iloc[-1]) if len(df) else 0.0
    return Signal(Direction.NONE, price, 0.0, 0.0, 0.0,
                  "no strategy configured yet")
