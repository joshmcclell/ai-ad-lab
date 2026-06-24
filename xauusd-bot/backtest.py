"""Simple historical backtester for the SMA/RSI/ATR strategy.

It replays closed bars one at a time and applies the SAME entry/exit/sizing rules
as the live bot (imported from strategy.py and risk.py), so what you test is what
you trade. Intrabar fills are approximated from each bar's high/low; when both the
stop and target are touched in one bar, the STOP is assumed to fill first (the
pessimistic, honest assumption).

Run with live MT5 history:
    python backtest.py --bars 5000

Run fully offline from a CSV (columns: time,open,high,low,close,tick_volume):
    python backtest.py --csv data/xauusd_h1.csv

Limitations (be honest with yourself): no spread/commission/slippage modelling by
default, no partial fills, and signals are evaluated on closed bars. Demo-forward-
test before risking anything real.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd

from config import CONFIG
from indicators import add_indicators
from risk import calculate_lot
from strategy import LONG, SHORT, evaluate


@dataclass
class SymbolSpec:
    """Minimal stand-in for MT5 symbol_info, used for lot sizing offline.

    Defaults reflect typical IC Markets XAUUSD specs (1 lot = 100 oz, so a $1
    gold move = $100 per lot). Override via CLI if your account differs.
    """
    trade_tick_value: float = 1.0    # account-currency value of one tick / lot
    trade_tick_size: float = 0.01    # price increment of one tick
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01


@dataclass
class Trade:
    side: str
    entry_time: pd.Timestamp
    entry: float
    sl: float
    tp: float
    volume: float
    exit_time: pd.Timestamp | None = None
    exit: float | None = None
    pnl: float = 0.0
    reason: str = ""


def _pnl(side: str, entry: float, exit_price: float, volume: float, spec: SymbolSpec) -> float:
    money_per_price_per_lot = spec.trade_tick_value / spec.trade_tick_size
    move = (exit_price - entry) if side == LONG else (entry - exit_price)
    return move * volume * money_per_price_per_lot


def run_backtest(df: pd.DataFrame, spec: SymbolSpec, start_balance: float = 10_000.0) -> dict:
    df = add_indicators(df).reset_index(drop=True)
    balance = start_balance
    equity_curve: list[float] = []
    trades: list[Trade] = []
    open_trade: Trade | None = None

    # Need at least 2 bars plus indicator warm-up before evaluating.
    warmup = max(CONFIG.sma_slow, CONFIG.atr_period) + 2

    for i in range(warmup, len(df)):
        bar = df.iloc[i]

        # 1) Manage an open trade against THIS bar's range.
        if open_trade is not None:
            hit = _check_exit(open_trade, bar)
            if hit is not None:
                exit_price, reason = hit
                open_trade.exit_time = bar["time"]
                open_trade.exit = exit_price
                open_trade.reason = reason
                open_trade.pnl = _pnl(open_trade.side, open_trade.entry, exit_price,
                                      open_trade.volume, spec)
                balance += open_trade.pnl
                trades.append(open_trade)
                open_trade = None

        # 2) Evaluate the strategy on history up to and including this bar.
        signal = evaluate(df.iloc[: i + 1])

        # 3) Reverse signal closes an opposite open trade at this bar's close.
        if open_trade is not None and signal.has_trade:
            opposite = SHORT if signal.side == LONG else LONG
            if open_trade.side == opposite:
                exit_price = float(bar["close"])
                open_trade.exit_time = bar["time"]
                open_trade.exit = exit_price
                open_trade.reason = "reverse signal"
                open_trade.pnl = _pnl(open_trade.side, open_trade.entry, exit_price,
                                      open_trade.volume, spec)
                balance += open_trade.pnl
                trades.append(open_trade)
                open_trade = None

        # 4) New entry (no stacking same direction; one position at a time here).
        if open_trade is None and signal.has_trade:
            lot = calculate_lot(balance, signal.entry, signal.stop_loss, spec)
            if lot.ok:
                open_trade = Trade(
                    side=signal.side,
                    entry_time=bar["time"],
                    entry=signal.entry,
                    sl=signal.stop_loss,
                    tp=signal.take_profit,
                    volume=lot.volume,
                )

        equity_curve.append(balance)

    return _summarise(trades, equity_curve, start_balance, balance)


def _check_exit(trade: Trade, bar) -> tuple[float, str] | None:
    """Return (exit_price, reason) if SL/TP is touched in this bar, else None."""
    high, low = float(bar["high"]), float(bar["low"])
    if trade.side == LONG:
        if low <= trade.sl:          # pessimistic: stop checked first
            return trade.sl, "stop"
        if high >= trade.tp:
            return trade.tp, "target"
    else:  # short
        if high >= trade.sl:
            return trade.sl, "stop"
        if low <= trade.tp:
            return trade.tp, "target"
    return None


def _summarise(trades: list[Trade], equity: list[float], start: float, end: float) -> dict:
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)

    peak = start
    max_dd = 0.0
    for v in equity:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)

    return {
        "start_balance": start,
        "end_balance": round(end, 2),
        "net_profit": round(end - start, 2),
        "return_pct": round((end / start - 1) * 100, 2) if start else 0.0,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(trades), 2) if trades else 0.0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else float("inf"),
        "max_drawdown": round(max_dd, 2),
        "avg_win": round(gross_win / len(wins), 2) if wins else 0.0,
        "avg_loss": round(-gross_loss / len(losses), 2) if losses else 0.0,
        "_trades": trades,
    }


def _load_from_mt5(bars: int) -> pd.DataFrame:
    from mt5_client import MT5Client  # local import so offline CSV runs need no MT5

    client = MT5Client()
    if not client.connect():
        raise SystemExit("Could not connect to MT5 for historical data.")
    try:
        return client.get_ohlcv(bars)
    finally:
        client.shutdown()


def _load_from_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["time"] = pd.to_datetime(df["time"])
    needed = {"time", "open", "high", "low", "close"}
    if not needed.issubset(df.columns):
        raise SystemExit(f"CSV must contain columns: {sorted(needed)}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest the XAUUSD SMA/RSI/ATR strategy.")
    parser.add_argument("--bars", type=int, default=5000, help="bars to pull from MT5")
    parser.add_argument("--csv", type=str, default=None, help="offline OHLCV CSV instead of MT5")
    parser.add_argument("--balance", type=float, default=10_000.0, help="starting balance")
    parser.add_argument("--tick-value", type=float, default=1.0, help="symbol trade_tick_value")
    parser.add_argument("--tick-size", type=float, default=0.01, help="symbol trade_tick_size")
    args = parser.parse_args()

    df = _load_from_csv(args.csv) if args.csv else _load_from_mt5(args.bars)
    spec = SymbolSpec(trade_tick_value=args.tick_value, trade_tick_size=args.tick_size)

    stats = run_backtest(df, spec, start_balance=args.balance)

    print("\n==================== BACKTEST RESULTS ====================")
    print(f"Period bars     : {len(df)}  ({df['time'].iloc[0]} -> {df['time'].iloc[-1]})")
    for key in ("start_balance", "end_balance", "net_profit", "return_pct",
                "trades", "wins", "losses", "win_rate_pct", "profit_factor",
                "max_drawdown", "avg_win", "avg_loss"):
        print(f"{key:<16}: {stats[key]}")
    print("==========================================================")
    print("Reminder: backtest results are NOT a promise of live performance. "
          "Forward-test on demo before going live.\n")


if __name__ == "__main__":
    main()
