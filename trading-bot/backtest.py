"""
backtest.py
===========
Event-driven backtester for the XAU/USD scalping strategy. It replays
historical 1-minute candles bar-by-bar through the SAME `strategy.evaluate()`
used live, so backtest and live behaviour stay identical.

Data sources
------------
* From MT5 (requires the terminal + MetaTrader5 package):
      python backtest.py --from-mt5 --days 30
* From a CSV you exported yourself (works anywhere, no terminal needed):
      python backtest.py --csv data/xauusd_m1.csv
  The CSV must have columns: time, open, high, low, close [, tick_volume]
  with `time` parseable by pandas (UTC recommended).

Modelling choices (kept conservative and explicit)
--------------------------------------------------
* Entry at the *next* bar's open after a signal closes (no look-ahead).
* Each bar after entry is checked for SL/TP using its high/low. If both the
  SL and TP fall inside the same bar we assume the WORSE outcome (SL first) —
  a pessimistic, honest assumption for a scalper.
* A configurable spread + slippage (in price) is applied to entries/exits.
* Position sizing uses the same risk module (max lot 0.05 enforced).
* The daily-loss guard and one-position-at-a-time rule are enforced.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd

from config import SETTINGS
from indicators import add_indicators
from risk import DailyLossGuard, calculate_lot_size
from strategy import Direction, evaluate
from trade_logger import TradeLogger, TradeRecord, get_logger


@dataclass
class BacktestParams:
    spread_price: float = 0.20      # typical XAUUSD spread in USD (~20 cents)
    slippage_price: float = 0.05    # extra adverse fill, USD
    starting_balance: float = 1000.0
    commission_per_lot: float = 7.0  # IC Markets Raw: ~$3.5/side/lot round-turn $7


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    if "time" not in df.columns:
        raise ValueError("CSV must contain a 'time' column.")
    df["time"] = pd.to_datetime(df["time"], utc=True)
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"CSV missing required column '{col}'.")
    if "tick_volume" not in df.columns:
        df["tick_volume"] = 0
    return df.sort_values("time").reset_index(drop=True)


def load_from_mt5(days: int) -> pd.DataFrame:
    from mt5_client import MT5Client
    log = get_logger("backtest")
    client = MT5Client(SETTINGS.broker, SETTINGS.symbol, log)
    client.connect()
    try:
        import MetaTrader5 as mt5
        to = datetime.now(timezone.utc)
        frm = to - timedelta(days=days)
        rates = mt5.copy_rates_range(SETTINGS.symbol.name, mt5.TIMEFRAME_M1, frm, to)
        if rates is None or len(rates) == 0:
            raise RuntimeError("No historical data returned from MT5.")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df[["time", "open", "high", "low", "close", "tick_volume"]]
    finally:
        client.disconnect()


def run_backtest(df: pd.DataFrame, params: BacktestParams,
                 settings=SETTINGS, out_csv: str = "logs/backtest_trades.csv"):
    log = get_logger("backtest", settings.runtime.log_level)
    s = settings
    df = add_indicators(df, s.strategy).reset_index(drop=True)

    trade_log = TradeLogger(out_csv)
    guard = DailyLossGuard(s.risk)
    guard.reset(params.starting_balance)

    balance = params.starting_balance
    spec_tick_size = s.symbol.contract_size  # placeholder; uses contract fallback
    trades: list[TradeRecord] = []

    open_trade: dict | None = None
    warmup = max(s.strategy.ema_slow_period, s.strategy.atr_period) + 2

    for i in range(warmup, len(df) - 1):
        bar = df.iloc[i]
        nxt = df.iloc[i + 1]
        bar_time = bar["time"].to_pydatetime()

        # --- Manage an open trade against THIS bar's range -----------------
        if open_trade is not None:
            hit = _check_exit(open_trade, bar)
            if hit is not None:
                exit_price, result = hit
                pnl = _trade_pnl(open_trade, exit_price, params)
                balance += pnl
                guard.register_closed_trade(pnl)
                rec = open_trade["record"]
                rec.close_time = str(bar_time)
                rec.exit_price = round(exit_price, 3)
                rec.result = result
                rec.pnl = round(pnl, 2)
                rec.balance_after = round(balance, 2)
                trade_log.write(rec)
                trades.append(rec)
                open_trade = None

        # --- Daily-loss guard & one-trade rule -----------------------------
        if open_trade is not None:
            continue
        if guard.is_blocked(balance, bar_time.date()):
            continue

        # --- Evaluate strategy on the just-closed bar ----------------------
        window = df.iloc[: i + 1]
        # Backtester ignores session/news time filters by default (check_time
        # False) so historical data without tz context still produces signals;
        # set check_time=True to also enforce the London-session window.
        sig = evaluate(window, s.strategy, s.session, bar_time, check_time=False)
        if not sig.is_trade:
            continue

        # --- Size & "enter" at next bar open (+spread/slippage) ------------
        sl_distance = abs(sig.entry - sig.stop_loss)
        sizing = calculate_lot_size(
            balance=balance, sl_distance_price=sl_distance, risk_cfg=s.risk,
            contract_size=s.symbol.contract_size)
        if sizing.lot <= 0:
            continue

        is_long = sig.direction == Direction.LONG
        fill = float(nxt["open"]) + (params.slippage_price if is_long
                                     else -params.slippage_price)
        # Re-anchor SL/TP to the actual fill so R:R is preserved.
        if is_long:
            sl = fill - sl_distance
            tp = fill + sl_distance * s.strategy.risk_reward_ratio
        else:
            sl = fill + sl_distance
            tp = fill - sl_distance * s.strategy.risk_reward_ratio

        rec = TradeRecord(
            open_time=str(nxt["time"].to_pydatetime()),
            symbol=s.symbol.name, direction=sig.direction.value, lot=sizing.lot,
            entry_price=round(fill, 3), stop_loss=round(sl, 3),
            take_profit=round(tp, 3), atr=round(sig.atr, 3),
            money_at_risk=round(sizing.money_at_risk, 2), comment=sig.reason)
        open_trade = {
            "is_long": is_long, "entry": fill, "sl": sl, "tp": tp,
            "lot": sizing.lot, "record": rec,
        }

    _print_report(trades, params, balance, log)
    return trades, balance


def _check_exit(trade: dict, bar) -> tuple[float, str] | None:
    """Return (exit_price, 'TP'/'SL') if this bar's range hit a level."""
    high, low = float(bar["high"]), float(bar["low"])
    if trade["is_long"]:
        hit_sl = low <= trade["sl"]
        hit_tp = high >= trade["tp"]
        if hit_sl and hit_tp:        # pessimistic: assume SL first
            return trade["sl"], "SL"
        if hit_sl:
            return trade["sl"], "SL"
        if hit_tp:
            return trade["tp"], "TP"
    else:
        hit_sl = high >= trade["sl"]
        hit_tp = low <= trade["tp"]
        if hit_sl and hit_tp:
            return trade["sl"], "SL"
        if hit_sl:
            return trade["sl"], "SL"
        if hit_tp:
            return trade["tp"], "TP"
    return None


def _trade_pnl(trade: dict, exit_price: float, params: BacktestParams) -> float:
    """P/L in account currency including spread cost and commission."""
    contract = SETTINGS.symbol.contract_size
    direction = 1 if trade["is_long"] else -1
    gross = (exit_price - trade["entry"]) * direction * trade["lot"] * contract
    spread_cost = params.spread_price * trade["lot"] * contract
    commission = params.commission_per_lot * trade["lot"]
    return gross - spread_cost - commission


def _print_report(trades, params, balance, log) -> None:
    n = len(trades)
    if n == 0:
        log.info("Backtest complete: 0 trades. Try a longer window or relax filters.")
        return
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    net = balance - params.starting_balance
    win_rate = 100.0 * len(wins) / n
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    log.info("================ BACKTEST REPORT ================")
    log.info("Trades:        %d", n)
    log.info("Win rate:      %.1f%% (%d W / %d L)", win_rate, len(wins), len(losses))
    log.info("Profit factor: %.2f", pf)
    log.info("Start balance: %.2f", params.starting_balance)
    log.info("End balance:   %.2f", balance)
    log.info("Net P/L:       %.2f (%.1f%%)", net,
             100.0 * net / params.starting_balance)
    log.info("Max lot used:  %.2f", max(t.lot for t in trades))
    log.info("=================================================")


def main() -> None:
    p = argparse.ArgumentParser(description="Backtest the XAU/USD scalper")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="Path to a 1m OHLC CSV file.")
    src.add_argument("--from-mt5", action="store_true",
                     help="Pull history from the MT5 terminal.")
    p.add_argument("--days", type=int, default=30, help="Days of history (MT5).")
    p.add_argument("--balance", type=float, default=1000.0,
                   help="Starting balance for the simulation.")
    p.add_argument("--spread", type=float, default=0.20, help="Spread in USD.")
    args = p.parse_args()

    df = load_csv(args.csv) if args.csv else load_from_mt5(args.days)
    params = BacktestParams(starting_balance=args.balance, spread_price=args.spread)
    run_backtest(df, params)


if __name__ == "__main__":
    main()
