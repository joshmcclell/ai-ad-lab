"""
bot.py
======
The live / demo trading loop. It ties together the MT5 client, the strategy,
the risk module and the CSV logger.

Run:
    python bot.py                 # uses DEMO_MODE from .env (default: demo)
    python bot.py --live          # explicitly allow live trading
    python bot.py --list-symbols  # print XAU* symbols, then exit
    python bot.py --once          # evaluate once and exit (smoke test)

SAFETY MODEL
------------
* DEMO_MODE=true (default) makes the bot REFUSE to trade a live account — it
  exits if MT5 reports the connected account is not a demo.
* `--live` flips DEMO_MODE off for this run, but the bot still prints a clear
  LIVE banner and only trades if you pass it deliberately.
* Only ONE position is ever open (max_open_trades = 1).
* The daily-loss guard halts new entries after -2% on the day.
* Lot size can never exceed 0.05 (enforced in risk.calculate_lot_size).
"""

from __future__ import annotations

import argparse
import time as _time
from datetime import datetime

import pandas as pd

from alerts import Notifier, print_chat_ids
from config import SETTINGS
from indicators import add_indicators
from mt5_client import MT5Client, MT5Error
from risk import DailyLossGuard, calculate_lot_size
from strategy import Direction, evaluate
from trade_logger import TradeLogger, TradeRecord, get_logger, utc_now_iso


class ScalpingBot:
    def __init__(self, settings=SETTINGS):
        self.s = settings
        self.log = get_logger("scalper", settings.runtime.log_level)
        self.client = MT5Client(settings.broker, settings.symbol, self.log)
        self.trade_log = TradeLogger(settings.runtime.trade_log_csv)
        self.guard = DailyLossGuard(settings.risk)
        self.notifier = Notifier(settings.alerts, self.log)
        self._spec = None
        self._last_bar_time = None        # de-dupe: one decision per closed bar
        self._open_record: TradeRecord | None = None
        self._daily_block_alerted = False  # avoid spamming the daily-loss alert

    # ------------------------------------------------------------------ #
    # Startup                                                             #
    # ------------------------------------------------------------------ #
    def start(self, allow_live: bool = False, run_once: bool = False) -> None:
        info = self.client.connect()
        self._spec = self.client.symbol_spec()
        self.log.info("Symbol spec: tick_size=%s tick_value=%s contract=%s "
                      "vol[min=%s step=%s max=%s]", self._spec.tick_size,
                      self._spec.tick_value, self._spec.contract_size,
                      self._spec.volume_min, self._spec.volume_step,
                      self._spec.volume_max)

        demo_required = self.s.runtime.demo_mode and not allow_live
        if demo_required and not info.is_demo:
            self.log.error("DEMO_MODE is on but the connected account is LIVE. "
                           "Refusing to trade. Pass --live to override.")
            self.client.disconnect()
            return
        if not info.is_demo:
            self.log.warning("=== LIVE ACCOUNT — REAL MONEY AT RISK ===")

        self.guard.reset(info.balance)
        mode = "DEMO" if info.is_demo else "LIVE"
        self.notifier.send(
            f"\U0001F916 Scalper started ({mode})\n"
            f"Account {info.login} on {info.server}\n"
            f"Balance: {info.balance:.2f} {info.currency}\n"
            f"Symbol: {self.s.symbol.name}")

        try:
            if run_once:
                self._tick()
            else:
                self._loop()
        except KeyboardInterrupt:
            self.log.info("Stopped by user.")
        finally:
            self.client.disconnect()

    # ------------------------------------------------------------------ #
    # Main loop                                                           #
    # ------------------------------------------------------------------ #
    def _loop(self) -> None:
        self.log.info("Entering trading loop (Ctrl-C to stop).")
        while True:
            try:
                self._tick()
            except MT5Error as e:
                self.log.error("MT5 error: %s", e)
            except Exception as e:  # keep the loop alive on unexpected errors
                self.log.exception("Unexpected error: %s", e)
            _time.sleep(self.s.runtime.poll_seconds)

    def _tick(self) -> None:
        # 1. Manage any open position first (detect TP/SL closure for logging).
        self._reconcile_open_position()

        # 2. Pull candles and compute indicators.
        df = self.client.get_candles(self.s.strategy.history_bars)
        latest_bar_time = df["time"].iloc[-1]

        # Only act once per newly-closed candle.
        if latest_bar_time == self._last_bar_time:
            return
        self._last_bar_time = latest_bar_time

        df = add_indicators(df, self.s.strategy)

        # 3. Risk gate: daily loss + max open trades.
        info = self.client.account_info()
        now_local = datetime.now(tz=self.s.tzinfo)

        if self.guard.is_blocked(info.balance, now_local.date()):
            self.log.info("Daily loss limit reached (%.2f). No new trades today.",
                          self.guard.realised_pnl)
            if not self._daily_block_alerted:
                self.notifier.send(
                    f"⛔ Daily loss limit hit ({self.guard.realised_pnl:.2f}). "
                    f"No new trades until tomorrow.")
                self._daily_block_alerted = True
            return
        self._daily_block_alerted = False  # reset once a new day clears the block

        if len(self.client.open_positions()) >= self.s.risk.max_open_trades:
            return  # already in a trade

        # 4. Evaluate the strategy.
        sig = evaluate(df, self.s.strategy, self.s.session, now_local,
                       check_time=True)
        if not sig.is_trade:
            self.log.debug("No entry (%s) @ %s", sig.reason, now_local.strftime("%H:%M"))
            return

        self._enter(sig, info)

    # ------------------------------------------------------------------ #
    # Entry                                                               #
    # ------------------------------------------------------------------ #
    def _enter(self, sig, info) -> None:
        sl_distance = abs(sig.entry - sig.stop_loss)
        sizing = calculate_lot_size(
            balance=info.balance,
            sl_distance_price=sl_distance,
            risk_cfg=self.s.risk,
            tick_size=self._spec.tick_size,
            tick_value=self._spec.tick_value,
            contract_size=self._spec.contract_size,
        )
        if sizing.lot <= 0:
            self.log.info("Skip %s: %s", sig.direction.value, sizing.skipped_reason)
            return

        self.log.info("Signal %s | risk %.2f %s | SLdist %.3f | lot %.2f%s | %s",
                      sig.direction.value, sizing.money_at_risk, info.currency,
                      sl_distance, sizing.lot,
                      " (capped@0.05)" if sizing.capped_by_max_lot else "",
                      sig.reason)

        is_long = sig.direction == Direction.LONG
        try:
            result = self.client.place_market_order(
                is_long, sizing.lot, sig.stop_loss, sig.take_profit,
                self.s.risk, comment="xauusd-scalper")
        except MT5Error as e:
            self.log.error("Entry failed: %s", e)
            self.notifier.send(f"⚠️ Entry failed ({sig.direction.value}): {e}")
            return

        self.notifier.send(
            f"\U0001F7E2 OPEN {sig.direction.value} {self.s.symbol.name}\n"
            f"Lot: {sizing.lot:.2f}{' (max 0.05 cap)' if sizing.capped_by_max_lot else ''}\n"
            f"Entry: {result.price:.3f}\n"
            f"SL: {sig.stop_loss:.3f}   TP: {sig.take_profit:.3f}\n"
            f"Risk: {sizing.money_at_risk:.2f} {info.currency}")

        self._open_record = TradeRecord(
            open_time=utc_now_iso(),
            symbol=self.s.symbol.name,
            direction=sig.direction.value,
            lot=sizing.lot,
            entry_price=result.price,
            stop_loss=sig.stop_loss,
            take_profit=sig.take_profit,
            atr=sig.atr,
            money_at_risk=sizing.money_at_risk,
            order_ticket=getattr(result, "order", None),
            comment=sig.reason,
        )

    # ------------------------------------------------------------------ #
    # Exit detection / logging                                            #
    # ------------------------------------------------------------------ #
    def _reconcile_open_position(self) -> None:
        """If our tracked position is no longer open, it hit TP/SL — log it."""
        if self._open_record is None:
            return
        positions = self.client.open_positions()
        still_open = any(getattr(p, "comment", "") or True for p in positions) \
            and len(positions) > 0
        if still_open:
            return

        # Position closed externally (TP/SL). Pull the realised P/L from history.
        rec = self._open_record
        info = self.client.account_info()
        pnl = self._lookup_last_deal_profit(rec)
        rec.close_time = utc_now_iso()
        rec.pnl = pnl
        rec.balance_after = info.balance
        rec.result = "WIN" if pnl >= 0 else "LOSS"
        rec.exit_price = self._estimate_exit_price(rec, pnl)
        self.trade_log.write(rec)
        self.guard.register_closed_trade(pnl)
        self.log.info("Trade closed: %s %s lot=%.2f pnl=%.2f -> balance %.2f",
                      rec.direction, rec.result, rec.lot, pnl, info.balance)
        emoji = "✅" if rec.result == "WIN" else "❌"
        self.notifier.send(
            f"{emoji} CLOSED {rec.direction} {self.s.symbol.name} {rec.result}\n"
            f"P/L: {pnl:.2f} {info.currency}\n"
            f"Balance: {info.balance:.2f} {info.currency}")
        self._open_record = None

    def _lookup_last_deal_profit(self, rec) -> float:
        """Best-effort realised P/L for the just-closed position from history."""
        try:
            import MetaTrader5 as mt5
            from datetime import timedelta, timezone
            now = datetime.now(timezone.utc)
            deals = mt5.history_deals_get(now - timedelta(days=1), now,
                                          group=f"*{self.s.symbol.name}*")
            if not deals:
                return 0.0
            mine = [d for d in deals if d.magic == self.s.risk.magic_number]
            if not mine:
                return 0.0
            # Sum profit of the most recent out-deal(s).
            last = sorted(mine, key=lambda d: d.time)[-1]
            return float(last.profit + last.commission + last.swap)
        except Exception:  # pragma: no cover
            return 0.0

    def _estimate_exit_price(self, rec, pnl: float) -> float:
        """Infer whether TP or SL was hit from the sign of the P/L."""
        if pnl >= 0:
            return rec.take_profit
        return rec.stop_loss


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="XAU/USD 1m scalping bot (MT5 / IC Markets)")
    parser.add_argument("--live", action="store_true",
                        help="Allow trading a LIVE account (overrides DEMO_MODE).")
    parser.add_argument("--once", action="store_true",
                        help="Evaluate a single time and exit (smoke test).")
    parser.add_argument("--list-symbols", action="store_true",
                        help="List XAU* symbols on the account and exit.")
    parser.add_argument("--test-alert", action="store_true",
                        help="Send a test Telegram alert and exit.")
    parser.add_argument("--telegram-setup", action="store_true",
                        help="Print your Telegram chat ID(s) and exit.")
    args = parser.parse_args()

    bot = ScalpingBot(SETTINGS)

    if args.telegram_setup:
        print_chat_ids(SETTINGS.alerts.telegram_token)
        return

    if args.test_alert:
        ok = bot.notifier.send_blocking(
            "✅ Test alert from your XAU/USD scalper — notifications are working!")
        print("Test alert sent." if ok else "Test alert failed — check the log "
              "above and your .env (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ALERTS).")
        return

    if args.list_symbols:
        bot.client.connect()
        print("Matching symbols:", bot.client.list_symbols("XAU"))
        bot.client.disconnect()
        return

    bot.start(allow_live=args.live, run_once=args.once)


if __name__ == "__main__":
    main()
