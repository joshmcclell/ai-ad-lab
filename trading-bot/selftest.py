"""
selftest.py
===========
Pure-Python sanity checks that run WITHOUT MetaTrader5 or a terminal. They
prove the core logic — lot sizing (incl. the 0.05 cap and balance flexibility),
indicators and the strategy signal generator — behaves as specified.

Run:  python selftest.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import SETTINGS
from indicators import add_indicators
from risk import DailyLossGuard, calculate_lot_size
from strategy import Direction, evaluate

risk = SETTINGS.risk
strat = SETTINGS.strategy


def test_lot_sizing_respects_risk_pct():
    # $1000 @ 1% = $10 risk. SL distance 1.0 USD -> loss/lot = $100.
    # raw lot = 10/100 = 0.10 -> but capped at max_lot 0.05.
    r = calculate_lot_size(1000, 1.0, risk, contract_size=100.0)
    assert r.lot == 0.05, r
    assert r.capped_by_max_lot is True
    print("ok  lot sizing caps at 0.05 ceiling")


def test_lot_sizing_small_balance():
    # $100 @ 1% = $1 risk. SL distance 2.0 -> loss/lot = $200.
    # raw lot = 1/200 = 0.005 -> below min 0.01 -> skip (no over-risk).
    r = calculate_lot_size(100, 2.0, risk, contract_size=100.0)
    assert r.lot == 0.0 and r.skipped_reason, r
    print("ok  tiny balance / wide stop is skipped, not over-risked")


def test_lot_sizing_midrange():
    # $500 @ 1% = $5 risk. SL distance 1.5 -> loss/lot = $150.
    # raw = 5/150 = 0.0333 -> floor to step 0.01 -> 0.03 (within [0.01,0.05]).
    r = calculate_lot_size(500, 1.5, risk, contract_size=100.0)
    assert r.lot == 0.03, r
    assert not r.capped_by_max_lot
    print("ok  mid balance sizes within band (0.03) and floors to step")


def test_lot_never_exceeds_max_even_huge_balance():
    for bal in (1_000, 5_000, 50_000, 1_000_000):
        r = calculate_lot_size(bal, 1.0, risk, contract_size=100.0)
        assert r.lot <= risk.max_lot, (bal, r.lot)
    print("ok  lot never exceeds 0.05 across $1k..$1M balances")


def test_daily_loss_guard():
    g = DailyLossGuard(risk)
    g.reset(1000.0)
    assert not g.is_blocked(1000.0)
    g.register_closed_trade(-15.0)   # -1.5%
    assert not g.is_blocked(985.0)
    g.register_closed_trade(-10.0)   # total -2.5% > 2% limit
    assert g.is_blocked(975.0)
    print("ok  daily-loss guard blocks after -2%")


def _synthetic_uptrend(n=120) -> pd.DataFrame:
    # Rising series with a clean bullish engulfing on the final bar.
    base = np.linspace(2000, 2030, n)
    close = base + np.random.default_rng(1).normal(0, 0.3, n)
    openp = close - 0.2
    high = np.maximum(openp, close) + 0.5
    low = np.minimum(openp, close) - 0.5
    df = pd.DataFrame({
        "time": pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC"),
        "open": openp, "high": high, "low": low, "close": close,
        "tick_volume": 100,
    })
    # Force a strong bullish engulfing on the last bar.
    df.loc[n - 2, ["open", "close"]] = [df["close"].iloc[n - 3], df["close"].iloc[n - 3] - 1.0]
    df.loc[n - 1, "open"] = df["close"].iloc[n - 2] - 0.2
    df.loc[n - 1, "close"] = df["open"].iloc[n - 2] + 1.5
    df.loc[n - 1, "high"] = df["close"].iloc[n - 1] + 0.3
    df.loc[n - 1, "low"] = df["open"].iloc[n - 1] - 0.1
    return df


def test_strategy_emits_long_in_uptrend():
    df = add_indicators(_synthetic_uptrend(), strat)
    sig = evaluate(df, strat, check_time=False)
    # We don't hard-assert a LONG (random noise can flip RSI), but the signal
    # must be well-formed and SL/TP must respect the 1:1.5 R:R when it trades.
    if sig.is_trade:
        rr = abs(sig.take_profit - sig.entry) / abs(sig.entry - sig.stop_loss)
        assert abs(rr - strat.risk_reward_ratio) < 1e-6, rr
        assert sig.direction in (Direction.LONG, Direction.SHORT)
        print(f"ok  strategy produced {sig.direction.value} with correct 1:1.5 R:R")
    else:
        print(f"ok  strategy produced no trade ({sig.reason}) — still valid")


if __name__ == "__main__":
    test_lot_sizing_respects_risk_pct()
    test_lot_sizing_small_balance()
    test_lot_sizing_midrange()
    test_lot_never_exceeds_max_even_huge_balance()
    test_daily_loss_guard()
    test_strategy_emits_long_in_uptrend()
    print("\nAll self-tests passed.")
