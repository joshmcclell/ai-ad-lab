"""
config.py
=========
Single source of truth for every tunable parameter in the XAU/USD scalping bot.

Nothing in the rest of the code base hard-codes a number that a trader might
reasonably want to change — it all lives here. Edit this file (or, for the
sensitive credentials, the `.env` file) and restart the bot.

Credentials are read from environment variables (loaded from a local `.env`
file) so that your MT5 login never ends up in source control.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# Load variables from a local .env file (if present) into the environment.
load_dotenv()


# --------------------------------------------------------------------------- #
# 1. BROKER / CONNECTION SETTINGS  (secrets come from .env, never hard-coded)  #
# --------------------------------------------------------------------------- #
@dataclass
class BrokerConfig:
    # IC Markets MT5 login credentials — set these in your .env file.
    login: int = int(os.getenv("MT5_LOGIN", "0") or "0")
    password: str = os.getenv("MT5_PASSWORD", "")

    # IC Markets server names look like:
    #   Demo  : "ICMarketsSC-Demo"   or  "ICMarkets-Demo"
    #   Live  : "ICMarketsSC-Live"   or  "ICMarketsSC-Live01" / "...-Live02"
    # The exact string is shown in MT5 under  File -> Login to Trade Account.
    # ALWAYS copy it from your own terminal — it varies per entity/region.
    server: str = os.getenv("MT5_SERVER", "ICMarketsSC-Demo")

    # Optional: full path to terminal64.exe. Leave blank to let the
    # MetaTrader5 package auto-detect an already-running terminal.
    terminal_path: str = os.getenv("MT5_TERMINAL_PATH", "")


# --------------------------------------------------------------------------- #
# 2. INSTRUMENT SETTINGS                                                       #
# --------------------------------------------------------------------------- #
@dataclass
class SymbolConfig:
    # IC Markets usually lists gold as plain "XAUUSD". Some account types add a
    # suffix (e.g. "XAUUSD.a", "XAUUSD."). If the bot reports "symbol not found"
    # run mt5_client.list_symbols() and copy the exact name here.
    name: str = os.getenv("MT5_SYMBOL", "XAUUSD")

    # Contract size = ounces of gold per 1.00 lot. Standard for XAUUSD = 100.
    # NB: the bot reads the *real* contract/tick specs from the broker at
    # runtime; this value is only a fallback used by the offline backtester.
    contract_size: float = 100.0


# --------------------------------------------------------------------------- #
# 3. STRATEGY / INDICATOR PARAMETERS                                           #
# --------------------------------------------------------------------------- #
@dataclass
class StrategyConfig:
    # Timeframe is fixed to 1-minute for this scalping strategy.
    timeframe_minutes: int = 1

    # --- Trend filter: dual EMA --------------------------------------------
    ema_fast_period: int = 20
    ema_slow_period: int = 50

    # --- Momentum filter: RSI ----------------------------------------------
    rsi_period: int = 7
    rsi_long_min: float = 40.0   # long only if RSI above this ...
    rsi_long_max: float = 70.0   # ... and below this (avoid overbought)
    rsi_short_min: float = 30.0  # short only if RSI above this (avoid oversold) ...
    rsi_short_max: float = 60.0  # ... and below this

    # --- Volatility filter: ATR --------------------------------------------
    atr_period: int = 5
    atr_min: float = 0.15        # skip entries when ATR (in price) < this

    # --- Candle confirmation -----------------------------------------------
    # Require an engulfing candle or a pin bar in the trade direction on the
    # signal candle. Set to False to trade on the EMA/RSI/ATR stack alone.
    require_candle_confirmation: bool = True

    # --- Risk / exit -------------------------------------------------------
    sl_atr_multiplier: float = 1.2     # stop-loss distance = 1.2 x ATR
    risk_reward_ratio: float = 1.5     # take-profit = 1.5 x risk (1:1.5)

    # How many of the most recent closed candles to pull for indicator calc.
    history_bars: int = 300


# --------------------------------------------------------------------------- #
# 4. RISK / MONEY-MANAGEMENT PARAMETERS                                        #
# --------------------------------------------------------------------------- #
@dataclass
class RiskConfig:
    risk_per_trade_pct: float = 1.0    # risk 1% of balance per trade
    max_daily_loss_pct: float = 2.0    # stop trading after -2% on the day
    max_open_trades: int = 1           # only ever one position open

    # Lot constraints. MAX_LOT is a hard ceiling — the sizing logic clamps to
    # it no matter how large the balance is. (Requirement: never exceed 0.05.)
    min_lot: float = 0.01
    max_lot: float = 0.05
    lot_step: float = 0.01             # IC Markets XAUUSD volume step

    # Order execution tolerances.
    deviation_points: int = 20         # max slippage (in points) we accept
    magic_number: int = 990101         # tags this bot's orders in MT5


# --------------------------------------------------------------------------- #
# 5. SESSION / TIME FILTER                                                     #
# --------------------------------------------------------------------------- #
@dataclass
class SessionConfig:
    # London session, expressed in "UTC+1" wall-clock as requested.
    # We anchor to Europe/London so the window automatically tracks GMT/BST.
    timezone: str = "Europe/London"
    session_start: time = time(8, 0)    # 08:00 local
    session_end: time = time(16, 0)     # 16:00 local

    # Trade around the clock? Set TRADE_24H=true in .env to ignore the
    # 08:00-16:00 window and let the bot trade at any hour. Default (false)
    # keeps the London-session filter on. NB: spreads widen outside
    # London/NY hours, so off-hours scalping costs more — the ATR filter still
    # blocks the dead, low-volatility minutes either way.
    enforce_session: bool = (
        os.getenv("TRADE_24H", "false").strip().lower()
        not in ("1", "true", "yes", "on"))

    # News blackout: skip trading this many minutes before AND after each
    # event. Populate `news_events` with known high-impact releases (NFP, CPI,
    # FOMC, etc.) as timezone-aware datetimes, or wire in a calendar feed.
    news_buffer_minutes: int = 15
    # list[datetime] — left empty by default; see README "News rule".
    news_events: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 6. RUNTIME / OPERATIONAL SETTINGS                                            #
# --------------------------------------------------------------------------- #
@dataclass
class RuntimeConfig:
    # DEMO MODE TOGGLE.
    #   True  -> the bot refuses to run against a real (live) account; it will
    #            only operate on an account MT5 flags as a demo. This is the
    #            safety default.
    #   False -> live trading is permitted.
    demo_mode: bool = (os.getenv("DEMO_MODE", "true").strip().lower()
                       in ("1", "true", "yes", "on"))

    # Seconds to wait between strategy evaluations in the live loop. The bot
    # actually syncs to candle closes, so this is just the polling granularity.
    poll_seconds: int = 5

    # Where trade history is written.
    trade_log_csv: str = os.getenv("TRADE_LOG_CSV", "logs/trades.csv")

    # General log verbosity for the console.
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


# --------------------------------------------------------------------------- #
# Convenience: one object that bundles everything together.                    #
# --------------------------------------------------------------------------- #
@dataclass
class Settings:
    broker: BrokerConfig = field(default_factory=BrokerConfig)
    symbol: SymbolConfig = field(default_factory=SymbolConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.session.timezone)


# A single shared instance the rest of the code imports.
SETTINGS = Settings()
