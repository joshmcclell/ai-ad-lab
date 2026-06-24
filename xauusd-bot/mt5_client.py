"""Thin, defensive wrapper around the MetaTrader5 package.

Responsibilities:
  - connect / login / auto-reconnect to the IC Markets MT5 terminal
  - resolve the gold symbol (handles broker suffixes like XAUUSD.a)
  - pull OHLCV history into a tidy pandas DataFrame
  - read account + symbol metadata used for lot sizing
  - place market orders with SL/TP and close positions

All MT5 calls are funneled through here so the rest of the bot never touches the
raw API and reconnection logic lives in exactly one place.
"""
from __future__ import annotations

import time as _time
from dataclasses import dataclass

import MetaTrader5 as mt5
import pandas as pd

from config import CONFIG
from logger import get_logger

log = get_logger()

# Map our human timeframe strings to MT5 constants.
_TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
}


@dataclass
class Position:
    ticket: int
    side: str          # "long" or "short"
    volume: float
    price_open: float
    sl: float
    tp: float
    profit: float


def timeframe_const() -> int:
    tf = _TF_MAP.get(CONFIG.timeframe)
    if tf is None:
        raise ValueError(
            f"Unknown TIMEFRAME '{CONFIG.timeframe}'. Use one of: {', '.join(_TF_MAP)}"
        )
    return tf


class MT5Client:
    def __init__(self) -> None:
        self.symbol: str | None = None

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #
    def connect(self) -> bool:
        """Initialise the terminal and log in. Returns True on success."""
        kwargs = {
            "login": CONFIG.login,
            "password": CONFIG.password,
            "server": CONFIG.server,
        }
        if CONFIG.terminal_path:
            ok = mt5.initialize(CONFIG.terminal_path, **kwargs)
        else:
            ok = mt5.initialize(**kwargs)

        if not ok:
            log.error("MT5 initialize() failed: %s", mt5.last_error())
            return False

        info = mt5.account_info()
        if info is None:
            log.error("Connected to terminal but account_info() is None: %s", mt5.last_error())
            return False

        kind = "LIVE" if info.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL else "DEMO/CONTEST"
        log.info(
            "Connected: login=%s server=%s (%s) balance=%.2f %s leverage=1:%s",
            info.login, CONFIG.server, kind, info.balance, info.currency, info.leverage,
        )

        # Cross-check the account type against the configured mode.
        account_is_real = info.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL
        if CONFIG.is_live and not account_is_real:
            log.warning("TRADE_MODE=live but the logged-in account is a DEMO account.")
        if not CONFIG.is_live and account_is_real:
            log.warning(
                "TRADE_MODE=demo but the logged-in account is a REAL/LIVE account. "
                "The bot will NOT send orders while in demo mode."
            )

        return self._resolve_symbol()

    def _resolve_symbol(self) -> bool:
        """Find and select the gold symbol, tolerating broker suffixes."""
        wanted = CONFIG.symbol
        if mt5.symbol_info(wanted) is not None:
            self.symbol = wanted
        else:
            # Search for close matches, e.g. XAUUSD.a / XAUUSD.i
            candidates = mt5.symbols_get("*XAUUSD*") or mt5.symbols_get("*XAU*")
            names = [s.name for s in candidates] if candidates else []
            if wanted in names:
                self.symbol = wanted
            elif names:
                self.symbol = names[0]
                log.warning(
                    "Symbol '%s' not found. Using closest match '%s'. "
                    "All gold-like symbols: %s. Set SYMBOL in .env to override.",
                    wanted, self.symbol, ", ".join(names),
                )
            else:
                log.error("No XAUUSD-like symbol available on this account.")
                return False

        if not mt5.symbol_select(self.symbol, True):
            log.error("Could not select symbol %s in Market Watch: %s", self.symbol, mt5.last_error())
            return False

        log.info("Using symbol: %s", self.symbol)
        return True

    def is_connected(self) -> bool:
        return mt5.terminal_info() is not None and mt5.account_info() is not None

    def ensure_connected(self, retries: int = 5) -> bool:
        """Reconnect with exponential backoff if the link dropped."""
        if self.is_connected():
            return True
        log.warning("MT5 connection lost. Attempting to reconnect...")
        mt5.shutdown()
        delay = 2
        for attempt in range(1, retries + 1):
            if self.connect():
                log.info("Reconnected on attempt %d.", attempt)
                return True
            log.warning("Reconnect attempt %d/%d failed; sleeping %ds.", attempt, retries, delay)
            _time.sleep(delay)
            delay = min(delay * 2, 60)
        log.error("Could not reconnect after %d attempts.", retries)
        return False

    def shutdown(self) -> None:
        mt5.shutdown()
        log.info("MT5 connection closed.")

    # ------------------------------------------------------------------ #
    # Market data
    # ------------------------------------------------------------------ #
    def get_ohlcv(self, bars: int | None = None, timeframe: int | None = None) -> pd.DataFrame:
        """Return the most recent `bars` candles as a DataFrame (oldest first)."""
        n = bars or CONFIG.history_bars
        tf = timeframe if timeframe is not None else timeframe_const()
        rates = mt5.copy_rates_from_pos(self.symbol, tf, 0, n)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No rates returned for {self.symbol}: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df[["time", "open", "high", "low", "close", "tick_volume", "spread"]]

    def closed_bars(self, bars: int | None = None) -> pd.DataFrame:
        """OHLCV with the still-forming current candle dropped — act on closed bars only."""
        df = self.get_ohlcv(bars)
        return df.iloc[:-1].reset_index(drop=True)

    def current_spread_points(self) -> int:
        tick = mt5.symbol_info_tick(self.symbol)
        info = mt5.symbol_info(self.symbol)
        if tick is None or info is None or info.point == 0:
            return 0
        return int(round((tick.ask - tick.bid) / info.point))

    # ------------------------------------------------------------------ #
    # Account / symbol metadata
    # ------------------------------------------------------------------ #
    def account_balance(self) -> float:
        info = mt5.account_info()
        return float(info.balance) if info else 0.0

    def account_equity(self) -> float:
        info = mt5.account_info()
        return float(info.equity) if info else 0.0

    def account_free_margin(self) -> float:
        info = mt5.account_info()
        return float(info.margin_free) if info else 0.0

    def account_is_real(self) -> bool:
        info = mt5.account_info()
        return bool(info and info.trade_mode == mt5.ACCOUNT_TRADE_MODE_REAL)

    def symbol_info(self):
        return mt5.symbol_info(self.symbol)

    # ------------------------------------------------------------------ #
    # Positions
    # ------------------------------------------------------------------ #
    def open_positions(self) -> list[Position]:
        """This bot's open positions on the symbol (filtered by magic number)."""
        raw = mt5.positions_get(symbol=self.symbol)
        result: list[Position] = []
        for p in raw or []:
            if p.magic != CONFIG.magic_number:
                continue
            result.append(
                Position(
                    ticket=p.ticket,
                    side="long" if p.type == mt5.POSITION_TYPE_BUY else "short",
                    volume=p.volume,
                    price_open=p.price_open,
                    sl=p.sl,
                    tp=p.tp,
                    profit=p.profit,
                )
            )
        return result

    # ------------------------------------------------------------------ #
    # Order execution
    # ------------------------------------------------------------------ #
    def _filling_mode(self):
        """Pick a fill mode the symbol actually supports (IC Markets = IOC/FOK)."""
        info = mt5.symbol_info(self.symbol)
        modes = getattr(info, "filling_mode", 0)
        if modes & 1:   # SYMBOL_FILLING_FOK
            return mt5.ORDER_FILLING_FOK
        if modes & 2:   # SYMBOL_FILLING_IOC
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    def open_market(self, side: str, volume: float, sl: float, tp: float, comment: str = "xauusd-bot"):
        """Send a market BUY/SELL with SL & TP. Returns the MT5 result object or None."""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            log.error("No tick for %s — cannot send order.", self.symbol)
            return None

        is_buy = side == "long"
        price = tick.ask if is_buy else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": float(volume),
            "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 30,
            "magic": CONFIG.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(),
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error("Order failed (%s): %s", getattr(result, "retcode", "None"),
                      getattr(result, "comment", mt5.last_error()))
            return None
        log.info("Opened %s %.2f lots @ %.3f sl=%.3f tp=%.3f ticket=%s",
                 side, volume, result.price, sl, tp, result.order)
        return result

    def close_position(self, pos: Position, comment: str = "xauusd-bot close"):
        """Close an open position with an opposite market deal."""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            log.error("No tick for %s — cannot close.", self.symbol)
            return None

        is_buy_close = pos.side == "short"  # to close a short you BUY
        price = tick.ask if is_buy_close else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_BUY if is_buy_close else mt5.ORDER_TYPE_SELL,
            "position": pos.ticket,
            "price": price,
            "deviation": 30,
            "magic": CONFIG.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(),
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            log.error("Close failed (%s): %s", getattr(result, "retcode", "None"),
                      getattr(result, "comment", mt5.last_error()))
            return None
        log.info("Closed %s ticket=%s (%.2f lots).", pos.side, pos.ticket, pos.volume)
        return result
