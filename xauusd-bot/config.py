"""Central configuration. Everything is read from environment variables / .env.

Import `CONFIG` (a frozen dataclass instance) anywhere you need a setting. Keeping
all tunables here is deliberate: change strategy/risk/instrument in one place
(your .env) without touching the trading logic.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env that sits next to this file (works regardless of cwd).
load_dotenv(Path(__file__).resolve().parent / ".env")


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def _hhmm(name: str, default: str) -> time:
    raw = _str(name, default) or default
    hh, mm = raw.split(":")
    return time(int(hh), int(mm))


@dataclass(frozen=True)
class Config:
    # --- Credentials / connection ---
    login: int = field(default_factory=lambda: _int("MT5_LOGIN", 0))
    password: str = field(default_factory=lambda: _str("MT5_PASSWORD"))
    server: str = field(default_factory=lambda: _str("MT5_SERVER"))
    terminal_path: str = field(default_factory=lambda: _str("MT5_TERMINAL_PATH"))

    # --- Mode / safety ---
    trade_mode: str = field(default_factory=lambda: _str("TRADE_MODE", "demo").lower())
    live_confirm: str = field(default_factory=lambda: _str("LIVE_CONFIRM"))

    # --- Instrument / timeframe ---
    symbol: str = field(default_factory=lambda: _str("SYMBOL", "XAUUSD"))
    timeframe: str = field(default_factory=lambda: _str("TIMEFRAME", "H1").upper())
    trade_hour_start: time = field(default_factory=lambda: _hhmm("TRADE_HOUR_START", "00:00"))
    trade_hour_end: time = field(default_factory=lambda: _hhmm("TRADE_HOUR_END", "23:59"))

    # --- Risk ---
    risk_per_trade: float = field(default_factory=lambda: _float("RISK_PER_TRADE", 0.01))
    risk_reward: float = field(default_factory=lambda: _float("RISK_REWARD", 2.0))
    daily_loss_limit: float = field(default_factory=lambda: _float("DAILY_LOSS_LIMIT", 0.03))

    # --- Stops ---
    sl_method: str = field(default_factory=lambda: _str("SL_METHOD", "atr").lower())
    atr_multiplier: float = field(default_factory=lambda: _float("ATR_MULTIPLIER", 1.5))
    swing_lookback: int = field(default_factory=lambda: _int("SWING_LOOKBACK", 10))

    # --- Indicators ---
    sma_fast: int = field(default_factory=lambda: _int("SMA_FAST", 50))
    sma_slow: int = field(default_factory=lambda: _int("SMA_SLOW", 200))
    rsi_period: int = field(default_factory=lambda: _int("RSI_PERIOD", 14))
    rsi_oversold: float = field(default_factory=lambda: _float("RSI_OVERSOLD", 30))
    rsi_overbought: float = field(default_factory=lambda: _float("RSI_OVERBOUGHT", 70))
    atr_period: int = field(default_factory=lambda: _int("ATR_PERIOD", 14))

    # --- Execution / loop ---
    magic_number: int = field(default_factory=lambda: _int("MAGIC_NUMBER", 990011))
    poll_seconds: int = field(default_factory=lambda: _int("POLL_SECONDS", 30))
    max_spread_points: int = field(default_factory=lambda: _int("MAX_SPREAD_POINTS", 0))

    # --- Alerts ---
    telegram_enabled: bool = field(default_factory=lambda: _bool("TELEGRAM_ENABLED", False))
    telegram_bot_token: str = field(default_factory=lambda: _str("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: str = field(default_factory=lambda: _str("TELEGRAM_CHAT_ID"))

    @property
    def is_live(self) -> bool:
        return self.trade_mode == "live"

    @property
    def history_bars(self) -> int:
        """How many bars to pull — enough for the slow SMA plus warm-up headroom."""
        return max(self.sma_slow, self.sma_fast, self.rsi_period, self.atr_period) + 250

    def validate(self) -> list[str]:
        """Return a list of human-readable problems (empty == OK)."""
        problems: list[str] = []
        if not self.login:
            problems.append("MT5_LOGIN is missing.")
        if not self.password:
            problems.append("MT5_PASSWORD is missing.")
        if not self.server:
            problems.append("MT5_SERVER is missing.")
        if self.sma_fast >= self.sma_slow:
            problems.append("SMA_FAST must be smaller than SMA_SLOW.")
        # Risk is user-configurable up to 100% per trade. Values above 10% are
        # aggressive and flagged loudly at startup (see bot.py), but not blocked.
        if not (0 < self.risk_per_trade <= 1.0):
            problems.append("RISK_PER_TRADE must be between 0 and 1.0 (0-100%).")
        if self.sl_method not in ("atr", "swing"):
            problems.append("SL_METHOD must be 'atr' or 'swing'.")
        if self.is_live and self.live_confirm != "YES_I_UNDERSTAND":
            problems.append(
                "TRADE_MODE=live requires LIVE_CONFIRM=YES_I_UNDERSTAND in your .env. "
                "Refusing to trade live without explicit confirmation."
            )
        return problems


CONFIG = Config()
