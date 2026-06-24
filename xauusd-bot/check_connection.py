"""Pre-flight check: verify MT5 connects, the symbol resolves and data flows.

Run this FIRST, before bot.py:   python check_connection.py
It never sends an order — it only reads. Use it to confirm your .env, server
name and symbol suffix are correct.
"""
from __future__ import annotations

from config import CONFIG
from indicators import add_indicators
from logger import get_logger
from mt5_client import MT5Client
from strategy import evaluate

log = get_logger()


def main() -> int:
    problems = CONFIG.validate()
    if problems:
        for p in problems:
            log.error("CONFIG: %s", p)
        return 1

    client = MT5Client()
    if not client.connect():
        log.error("Connection FAILED. Check the terminal is open, logged in, and "
                  "'Algo Trading' is enabled, plus MT5_SERVER spelling.")
        return 1

    try:
        info = client.symbol_info()
        log.info("Symbol %s: digits=%s point=%s lot[min/step/max]=%s/%s/%s "
                 "tick_value=%s tick_size=%s",
                 client.symbol, info.digits, info.point,
                 info.volume_min, info.volume_step, info.volume_max,
                 info.trade_tick_value, info.trade_tick_size)
        log.info("Spread now: %d points", client.current_spread_points())

        df = client.closed_bars()
        log.info("Pulled %d closed %s bars (latest %s).",
                 len(df), CONFIG.timeframe, df["time"].iloc[-1])

        df = add_indicators(df)
        sig = evaluate(df)
        last = df.iloc[-1]
        log.info("Latest indicators: sma_fast=%.3f sma_slow=%.3f rsi=%.2f atr=%.3f",
                 last["sma_fast"], last["sma_slow"], last["rsi"], last["atr"])
        log.info("Current signal: side=%s reason=%s", sig.side, sig.reason)
        log.info("All checks passed. You can now run:  python bot.py")
        return 0
    finally:
        client.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
