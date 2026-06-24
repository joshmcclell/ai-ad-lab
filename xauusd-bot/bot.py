"""Main live/demo trading loop.

Run:   python bot.py

Default behaviour is SAFE: it trades only on a demo account. To trade live you
must set BOTH  TRADE_MODE=live  AND  LIVE_CONFIRM=YES_I_UNDERSTAND  in .env.

Flow each cycle:
  1. ensure the MT5 connection is alive (auto-reconnect with backoff)
  2. respect the trading-hours window and the daily loss limit
  3. pull closed bars, compute indicators, evaluate the strategy
  4. manage positions: close on a reverse signal, never stack same-direction
  5. size the trade to 1% risk, check margin, send the order
"""
from __future__ import annotations

import sys
import time
from datetime import datetime

from config import CONFIG
from indicators import add_indicators
from logger import get_logger
from mt5_client import MT5Client
from risk import DailyLossGuard, calculate_lot, margin_ok
from strategy import LONG, SHORT, Signal, evaluate
import notifier

log = get_logger()

DISCLAIMER = (
    "=================================================================\n"
    "  XAU/USD MT5 BOT — EDUCATIONAL USE ONLY.\n"
    "  Trading is risky, especially leveraged products like XAUUSD.\n"
    "  IC Markets terms and fees apply. ALWAYS test on demo first.\n"
    "  You are responsible for your own trading decisions.\n"
    "================================================================="
)


def within_trading_hours(now: datetime) -> bool:
    start, end = CONFIG.trade_hour_start, CONFIG.trade_hour_end
    t = now.time()
    if start <= end:
        return start <= t <= end
    # Window wraps past midnight.
    return t >= start or t <= end


class TradingBot:
    def __init__(self, client: MT5Client) -> None:
        self.client = client
        self.guard = DailyLossGuard()
        self._last_bar_time = None
        # Order sending is disabled if we're in demo mode but logged into a REAL
        # account — a deliberate guard against accidentally trading real money.
        self.orders_enabled = True

    def _evaluate_safety(self) -> None:
        if not CONFIG.is_live and self.client.account_is_real():
            self.orders_enabled = False
            log.warning(
                "SAFETY: demo mode + REAL account detected -> running in DRY-RUN "
                "(signals logged, NO orders sent). Use a demo login to actually trade."
            )
        elif CONFIG.is_live:
            log.warning("LIVE TRADING IS ENABLED. Real money is at risk.")
        else:
            log.info("Demo mode: orders will be sent to the demo account.")

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        log.info(DISCLAIMER)
        self._evaluate_safety()
        log.info(
            "Strategy: SMA%d/%d trend + RSI%d cross (%s/%s), SL=%s, RR=1:%.1f, risk=%.1f%%",
            CONFIG.sma_fast, CONFIG.sma_slow, CONFIG.rsi_period,
            CONFIG.rsi_oversold, CONFIG.rsi_overbought, CONFIG.sl_method,
            CONFIG.risk_reward, CONFIG.risk_per_trade * 100,
        )
        if CONFIG.risk_per_trade > 0.10:
            log.warning(
                "HIGH RISK: RISK_PER_TRADE=%.0f%% per trade. A few consecutive losses "
                "can wipe the account. You disabled the 1%% safety on purpose.",
                CONFIG.risk_per_trade * 100,
            )
        if CONFIG.daily_loss_limit <= 0:
            log.warning("DAILY LOSS LIMIT DISABLED — the bot will not pause after losing days.")

        while True:
            try:
                self._cycle()
            except KeyboardInterrupt:
                log.info("Interrupted by user — shutting down.")
                break
            except Exception as exc:  # noqa: BLE001 — keep the loop alive, log everything
                log.exception("Unhandled error in cycle: %s", exc)
            time.sleep(CONFIG.poll_seconds)

    # ------------------------------------------------------------------ #
    def _cycle(self) -> None:
        if not self.client.ensure_connected():
            return

        balance = self.client.account_balance()

        # Daily loss limit (still manages exits, just blocks NEW entries).
        trading_allowed = self.guard.check(balance)

        # Trading-hours filter.
        if not within_trading_hours(datetime.now()):
            return

        # Spread guard (optional).
        if CONFIG.max_spread_points > 0:
            spread = self.client.current_spread_points()
            if spread > CONFIG.max_spread_points:
                log.info("Spread %d > max %d — skipping.", spread, CONFIG.max_spread_points)
                return

        df = self.client.closed_bars()
        if df.empty:
            return
        df = add_indicators(df)

        latest_bar_time = df["time"].iloc[-1]
        new_bar = latest_bar_time != self._last_bar_time

        signal = evaluate(df)
        positions = self.client.open_positions()

        # --- Manage existing positions on every cycle (exits are time-sensitive) ---
        self._manage_positions(positions, signal)

        # --- Only consider NEW entries once per freshly closed bar ---
        if not new_bar:
            return
        self._last_bar_time = latest_bar_time

        if not signal.has_trade:
            log.info("Bar %s | %s", latest_bar_time, signal.reason)
            return

        if not trading_allowed:
            log.info("Signal '%s' ignored — daily loss limit active.", signal.side)
            return

        # No duplicate positions in the same direction.
        if any(p.side == signal.side for p in self.client.open_positions()):
            log.info("Already in a %s position — not stacking.", signal.side)
            return

        self._open_trade(signal, balance)

    # ------------------------------------------------------------------ #
    def _manage_positions(self, positions: list, signal: Signal) -> None:
        """Close positions that are opposite to a fresh reverse signal."""
        if not signal.has_trade:
            return
        opposite = SHORT if signal.side == LONG else LONG
        for pos in positions:
            if pos.side == opposite:
                log.info("Reverse %s signal -> closing opposite %s position %s.",
                         signal.side, pos.side, pos.ticket)
                if self.orders_enabled:
                    self.client.close_position(pos)
                    notifier.send(f"Closed {pos.side} {self.client.symbol} on reverse signal.")

    def _open_trade(self, signal: Signal, balance: float) -> None:
        info = self.client.symbol_info()
        if info is None:
            log.error("No symbol info — cannot size trade.")
            return

        lot = calculate_lot(balance, signal.entry, signal.stop_loss, info)
        if not lot.ok:
            log.warning("Trade skipped: %s", lot.reason)
            return

        if not margin_ok(signal.side, lot.volume, signal.entry,
                         self.client.symbol, self.client.account_free_margin()):
            return

        log.info("SIGNAL %s | %s | entry~%.3f sl=%.3f tp=%.3f vol=%.2f",
                 signal.side.upper(), signal.reason, signal.entry,
                 signal.stop_loss, signal.take_profit, lot.volume)

        if not self.orders_enabled:
            log.info("DRY-RUN: order not sent (safety).")
            return

        result = self.client.open_market(signal.side, lot.volume, signal.stop_loss, signal.take_profit)
        if result is not None:
            notifier.send(
                f"Opened {signal.side.upper()} {self.client.symbol} {lot.volume} lots\n"
                f"entry~{result.price:.3f} sl={signal.stop_loss:.3f} tp={signal.take_profit:.3f}\n"
                f"{signal.reason}"
            )


def main() -> int:
    print(DISCLAIMER)
    problems = CONFIG.validate()
    if problems:
        log.error("Configuration errors:")
        for p in problems:
            log.error("  - %s", p)
        log.error("Fix your .env (copy from .env.example) and try again.")
        return 1

    client = MT5Client()
    if not client.connect():
        log.error("Could not connect to MT5. Is the terminal running and logged in?")
        return 1

    try:
        TradingBot(client).run()
    finally:
        client.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
