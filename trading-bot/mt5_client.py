"""
mt5_client.py
=============
Thin, defensive wrapper around the official `MetaTrader5` Python package.

Responsibilities:
  * connect to / disconnect from the IC Markets MT5 terminal
  * verify the symbol exists and is tradable, exposing its real contract specs
  * fetch live 1-minute candles as a pandas DataFrame
  * read account info (balance, currency, demo/live flag)
  * place market orders with SL/TP and close positions
  * surface clear errors for connection issues, missing data, invalid orders
    and margin problems instead of failing silently

The MetaTrader5 package only runs on Windows (or Wine). If it is not installed
this module still imports — the methods raise a clear RuntimeError so the rest
of the code (e.g. the backtester) can be used without a terminal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

try:
    import MetaTrader5 as mt5
    _HAS_MT5 = True
except Exception:  # pragma: no cover - platform dependent
    mt5 = None
    _HAS_MT5 = False


class MT5Error(RuntimeError):
    """Raised for any MT5-related failure with broker context attached."""


@dataclass
class SymbolSpec:
    name: str
    digits: int
    point: float
    tick_size: float
    tick_value: float          # profit/loss of one tick for 1.00 lot
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    trade_stops_level: int     # min SL/TP distance from price, in points


@dataclass
class AccountInfo:
    login: int
    balance: float
    equity: float
    margin_free: float
    currency: str
    leverage: int
    is_demo: bool
    server: str


# Map our minute-count to an MT5 timeframe constant.
def _timeframe(minutes: int):
    if not _HAS_MT5:
        return None
    mapping = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1,
    }
    if minutes not in mapping:
        raise MT5Error(f"unsupported timeframe: {minutes} minutes")
    return mapping[minutes]


class MT5Client:
    def __init__(self, broker_cfg, symbol_cfg, logger):
        self.broker = broker_cfg
        self.symbol_cfg = symbol_cfg
        self.log = logger
        self._connected = False

    # ------------------------------------------------------------------ #
    # Connection lifecycle                                                #
    # ------------------------------------------------------------------ #
    def connect(self) -> AccountInfo:
        if not _HAS_MT5:
            raise MT5Error(
                "The MetaTrader5 package is not available in this environment. "
                "Install it on Windows with `pip install MetaTrader5` and run "
                "the bot alongside the IC Markets MT5 terminal."
            )

        init_kwargs = dict(
            login=self.broker.login,
            password=self.broker.password,
            server=self.broker.server,
        )
        if self.broker.terminal_path:
            init_kwargs["path"] = self.broker.terminal_path

        if not mt5.initialize(**init_kwargs):
            code, msg = mt5.last_error()
            raise MT5Error(f"MT5 initialize() failed [{code}]: {msg}. "
                           f"Check terminal is installed, login/password/server "
                           f"are correct, and 'Algo Trading' is enabled.")

        # initialize() with credentials usually logs in, but be explicit.
        if self.broker.login:
            if not mt5.login(self.broker.login,
                             password=self.broker.password,
                             server=self.broker.server):
                code, msg = mt5.last_error()
                mt5.shutdown()
                raise MT5Error(f"MT5 login() failed [{code}]: {msg}. "
                               f"Verify IC Markets login {self.broker.login} and "
                               f"server '{self.broker.server}'.")

        self._connected = True
        info = self.account_info()
        self.log.info(
            "Connected to MT5 — account %s on %s | balance %.2f %s | %s",
            info.login, info.server, info.balance, info.currency,
            "DEMO" if info.is_demo else "LIVE",
        )
        self._ensure_symbol()
        return info

    def disconnect(self) -> None:
        if _HAS_MT5 and self._connected:
            mt5.shutdown()
            self._connected = False
            self.log.info("Disconnected from MT5.")

    # ------------------------------------------------------------------ #
    # Symbol handling                                                     #
    # ------------------------------------------------------------------ #
    def _ensure_symbol(self) -> None:
        name = self.symbol_cfg.name
        info = mt5.symbol_info(name)
        if info is None:
            raise MT5Error(
                f"Symbol '{name}' not found on this account. IC Markets may "
                f"list gold with a suffix (e.g. 'XAUUSD.a'). Run "
                f"list_symbols('XAU') to find the exact name and set MT5_SYMBOL."
            )
        if not info.visible:
            if not mt5.symbol_select(name, True):
                raise MT5Error(f"Could not add symbol '{name}' to Market Watch.")

    def list_symbols(self, contains: str = "XAU") -> list[str]:
        """Diagnostic helper — list tradable symbols matching a substring."""
        if not _HAS_MT5:
            raise MT5Error("MetaTrader5 not available.")
        symbols = mt5.symbols_get()
        return [s.name for s in symbols if contains.upper() in s.name.upper()]

    def symbol_spec(self) -> SymbolSpec:
        name = self.symbol_cfg.name
        s = mt5.symbol_info(name)
        if s is None:
            raise MT5Error(f"symbol_info('{name}') returned None.")
        return SymbolSpec(
            name=s.name,
            digits=s.digits,
            point=s.point,
            tick_size=s.trade_tick_size or s.point,
            tick_value=s.trade_tick_value,
            contract_size=s.trade_contract_size,
            volume_min=s.volume_min,
            volume_max=s.volume_max,
            volume_step=s.volume_step,
            trade_stops_level=s.trade_stops_level,
        )

    # ------------------------------------------------------------------ #
    # Account / market data                                               #
    # ------------------------------------------------------------------ #
    def account_info(self) -> AccountInfo:
        a = mt5.account_info()
        if a is None:
            raise MT5Error("account_info() returned None — not logged in?")
        is_demo = (getattr(a, "trade_mode", 0) == getattr(mt5,
                   "ACCOUNT_TRADE_MODE_DEMO", 0))
        return AccountInfo(
            login=a.login, balance=a.balance, equity=a.equity,
            margin_free=a.margin_free, currency=a.currency,
            leverage=a.leverage, is_demo=is_demo, server=a.server,
        )

    def get_candles(self, count: int) -> pd.DataFrame:
        """Fetch the most recent `count` closed M1 candles as a DataFrame."""
        tf = _timeframe(self.symbol_cfg_timeframe())
        # pos=1 -> start from the last *closed* bar (skip the forming candle).
        rates = mt5.copy_rates_from_pos(self.symbol_cfg.name, tf, 1, count)
        if rates is None or len(rates) == 0:
            code, msg = mt5.last_error()
            raise MT5Error(f"No price data for {self.symbol_cfg.name} [{code}]: "
                           f"{msg}. Market may be closed or symbol unavailable.")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.rename(columns={"tick_volume": "tick_volume"})
        return df[["time", "open", "high", "low", "close", "tick_volume"]]

    def symbol_cfg_timeframe(self) -> int:
        # Strategy timeframe is fixed at 1m; kept as a hook for flexibility.
        return 1

    def current_tick(self):
        tick = mt5.symbol_info_tick(self.symbol_cfg.name)
        if tick is None:
            raise MT5Error(f"No tick for {self.symbol_cfg.name}.")
        return tick

    # ------------------------------------------------------------------ #
    # Order management                                                    #
    # ------------------------------------------------------------------ #
    def open_positions(self) -> list:
        positions = mt5.positions_get(symbol=self.symbol_cfg.name)
        return list(positions) if positions else []

    def check_margin(self, direction_is_long: bool, lot: float, price: float) -> bool:
        """Verify free margin covers the order before sending it."""
        order_type = mt5.ORDER_TYPE_BUY if direction_is_long else mt5.ORDER_TYPE_SELL
        margin = mt5.order_calc_margin(order_type, self.symbol_cfg.name, lot, price)
        if margin is None:
            code, msg = mt5.last_error()
            raise MT5Error(f"order_calc_margin failed [{code}]: {msg}")
        free = self.account_info().margin_free
        if margin > free:
            self.log.warning("Insufficient margin: need %.2f, free %.2f",
                             margin, free)
            return False
        return True

    def place_market_order(self, direction_is_long: bool, lot: float,
                           sl: float, tp: float, risk_cfg,
                           comment: str = "scalper"):
        """
        Send a market order with attached SL/TP. Returns the MT5 result object.
        Raises MT5Error on a rejected/failed order.
        """
        tick = self.current_tick()
        price = tick.ask if direction_is_long else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if direction_is_long else mt5.ORDER_TYPE_SELL

        spec = self.symbol_spec()
        # Respect broker minimum stop distance (trade_stops_level, in points).
        min_dist = spec.trade_stops_level * spec.point
        if min_dist > 0:
            if direction_is_long:
                sl = min(sl, price - min_dist)
                tp = max(tp, price + min_dist)
            else:
                sl = max(sl, price + min_dist)
                tp = min(tp, price - min_dist)

        sl = round(sl, spec.digits)
        tp = round(tp, spec.digits)

        if not self.check_margin(direction_is_long, lot, price):
            raise MT5Error("Margin check failed — order not sent.")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol_cfg.name,
            "volume": float(lot),
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": risk_cfg.deviation_points,
            "magic": risk_cfg.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(),
        }
        result = mt5.order_send(request)
        if result is None:
            code, msg = mt5.last_error()
            raise MT5Error(f"order_send returned None [{code}]: {msg}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise MT5Error(f"Order rejected: retcode={result.retcode} "
                           f"({result.comment})")
        self.log.info("Order filled: %s %.2f lots @ %.3f SL=%.3f TP=%.3f",
                      "BUY" if direction_is_long else "SELL", lot,
                      result.price, sl, tp)
        return result

    def _filling_mode(self):
        """Pick a filling mode the symbol supports (IC Markets = IOC/FOK)."""
        spec = mt5.symbol_info(self.symbol_cfg.name)
        mode = getattr(spec, "filling_mode", 0)
        # filling_mode is a bitmask; prefer IOC, then FOK, else RETURN.
        if mode & 2:   # SYMBOL_FILLING_IOC
            return mt5.ORDER_FILLING_IOC
        if mode & 1:   # SYMBOL_FILLING_FOK
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN

    def close_position(self, position, risk_cfg, comment: str = "close"):
        """Market-close an open position. Returns the MT5 result object."""
        tick = self.current_tick()
        is_long = position.type == mt5.POSITION_TYPE_BUY
        price = tick.bid if is_long else tick.ask
        order_type = mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol_cfg.name,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": risk_cfg.deviation_points,
            "magic": risk_cfg.magic_number,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling_mode(),
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code, msg = mt5.last_error()
            raise MT5Error(f"Failed to close position {position.ticket}: "
                           f"{msg} (retcode "
                           f"{getattr(result, 'retcode', 'n/a')})")
        return result
