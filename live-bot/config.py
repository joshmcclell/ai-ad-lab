"""
config.py
=========
Single source of truth for every tunable parameter in the XAU/USD scalping bot.

Nothing in the rest of the code base hard-codes a number that a trader might
reasonably want to change - it all lives here. Edit this file (or, for the
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
    # IC Markets MT5 login credentials - set these in your .env file.
    login: int = int(os.getenv("MT5_LOGIN", "0") or "0")
    password: str = os.getenv("MT5_PASSWORD", "")

    # IC Markets server names look like:
    #   Demo  : "ICMarketsSC-Demo"   or  "ICMarkets-Demo"
    #   Live  : "ICMarketsSC-Live"   or  "ICMarketsSC-Live01" / "...-Live02"
    # The exact string is shown in MT5 under  File -> Login to Trade Account.
    # ALWAYS copy it from your own terminal - it varies per entity/region.
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

    # --- Momentum filter: RSI(7) -- mean-reversion pullback bands -----------
    rsi_period: int = 7
    rsi_long_min: float = 35.0   # LONG only when RSI is in a pullback dip ...
    rsi_long_max: float = 48.0   # ... 35-48 (correction, not oversold)
    rsi_short_min: float = 52.0  # SHORT only when RSI is in a pullback rally ...
    rsi_short_max: float = 65.0  # ... 52-65 (correction, not overbought)

    # --- Volatility filter: ATR(5) -----------------------------------------
    atr_period: int = 5
    atr_min: float = 0.12        # skip entries when ATR (in price) < this

    # --- Candle / pullback shape -------------------------------------------
    # "No large wick down/up": reject the signal candle if the wick AGAINST the
    # trade is bigger than this multiple of the body (a long opposing wick means
    # the level was rejected). Lower = stricter.
    max_wick_to_body: float = 1.0

    # --- Risk / exit -- MEAN REVERSION SCALPING, 1:1 -----------------------
    # Stop and target are BOTH 1.0 x ATR (1:1 reward-to-risk). Hard SL/TP are
    # attached to the order at entry, so the broker manages the exit even if the
    # bot/Wine drops. 1:1 is chosen for a high hit-rate mean-reversion bounce.
    sl_atr_multiplier: float = 1.0     # stop-loss distance = 1.0 x ATR
    risk_reward_ratio: float = 1.0     # take-profit = 1.0 x stop (1:1)

    # Spread filter (LIVE only): skip a trade when the broker spread exceeds this
    # many POINTS. NOTE: for IC Markets XAUUSD 1 point = 0.01, and raw gold
    # spread is typically ~15-30 points - so the spec's 2.0 will likely block
    # every trade. Override in .env with MAX_SPREAD_POINTS=25 if nothing fires.
    max_spread_points: float = float(os.getenv("MAX_SPREAD_POINTS", "2.0") or "2.0")

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

    # Lot constraints. MAX_LOT is a hard ceiling - the sizing logic clamps to
    # it no matter how large the balance is. (Requirement: never exceed 0.05.)
    min_lot: float = 0.01
    max_lot: float = 0.05
    lot_step: float = 0.01             # IC Markets XAUUSD volume step

    # On a small account the risk-correct size can fall BELOW the 0.01 minimum
    # (a wide gold stop + tiny balance). Default behaviour is to skip those
    # trades rather than over-risk. Set ALLOW_MIN_LOT=true in .env to trade the
    # 0.01 minimum anyway - accepting that such trades risk a little more than
    # risk_per_trade_pct. The 0.05 ceiling and 2% daily-loss stop still apply.
    allow_min_lot: bool = (os.getenv("ALLOW_MIN_LOT", "false").strip().lower()
                           in ("1", "true", "yes", "on"))

    # FIXED LOT - THIS STRATEGY USES EXACTLY 0.05 ON EVERY TRADE.
    # Every order is sent with volume = fixed_lot, no dynamic sizing (still
    # clamped to the broker's own min/max volume so the order is valid).
    # Override in .env with FIXED_LOT=... if you ever want a different size.
    fixed_lot: float = float(os.getenv("FIXED_LOT", "0.05") or "0.05")

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
    # London/NY hours, so off-hours scalping costs more - the ATR filter still
    # blocks the dead, low-volatility minutes either way.
    enforce_session: bool = (
        os.getenv("TRADE_24H", "false").strip().lower()
        not in ("1", "true", "yes", "on"))

    # News blackout: skip trading this many minutes before AND after each
    # event. Populate `news_events` with known high-impact releases (NFP, CPI,
    # FOMC, etc.) as timezone-aware datetimes, or wire in a calendar feed.
    news_buffer_minutes: int = 15
    # list[datetime] - left empty by default; see README "News rule".
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
# 7. ALERTS (Telegram push notifications)                                      #
# --------------------------------------------------------------------------- #
@dataclass
class AlertConfig:
    # Master switch. Set ALERTS=true in .env once the two values below are set.
    enabled: bool = (os.getenv("ALERTS", "false").strip().lower()
                     in ("1", "true", "yes", "on"))
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")


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
    alerts: AlertConfig = field(default_factory=AlertConfig)

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.session.timezone)


# A single shared instance the rest of the code imports.
SETTINGS = Settings()
