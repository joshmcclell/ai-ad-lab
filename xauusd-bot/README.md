# XAU/USD Trading Bot — IC Markets + MetaTrader 5

A Python trading bot for **gold (XAUUSD)** that connects to **IC Markets** via the
official **MetaTrader 5** Python API. It runs a transparent, mechanical strategy
(SMA trend filter + RSI cross entries, ATR/swing stops, fixed risk-reward) with
strict 1%-per-trade risk management, a daily loss limit, full logging, auto-
reconnect, optional Telegram alerts, and a backtester.

> ## ⚠️ Disclaimer — read this
> **This is for educational purposes only. Trading involves risk of loss,
> especially with leveraged products like XAUUSD. IC Markets terms and fees apply.
> Always test on demo first — you are responsible for your own trading decisions.**
>
> The bot ships in **demo mode by default** and refuses to trade live unless you
> explicitly opt in (see [Going live](#7-going-live-only-after-demo)).

---

## A note on the included ICT transcript

The request bundled a transcript of discretionary "Inner Circle Trader" commentary
(fair value gaps, volume imbalances, consequent encroachment, liquidity runs).
That is a **visual, discretionary** method — it does not reduce to the precise,
backtestable rules the spec asked for, and encoding a caricature of it would be
misleading. This bot therefore implements the **explicit SMA/RSI/ATR strategy**
from the brief, which is mechanical and testable. Treat the transcript as
background reading, not as logic in the code.

---

## 1. Requirements & important platform note

- **Python 3.10+**
- The `MetaTrader5` Python package **only runs on Windows** (or on Linux/macOS
  through Wine + a Windows Python, which is fiddly). This is a limitation of
  MetaQuotes' library, not this bot. Run the bot on the **same machine** as the
  MT5 terminal, or on a cheap Windows VPS — the way virtually everyone runs MT5
  bots.
- The strategy/backtest/risk code is plain pandas and can be developed and
  **backtested offline on any OS from a CSV** (no MT5 needed); only the *live*
  connection requires Windows + MT5.

---

## 2. Install

```bash
# 1. Install the MetaTrader 5 desktop terminal for IC Markets and log in
#    (Download it from IC Markets > Trading Platforms > MetaTrader 5).

# 2. Get the bot code, then from this folder:
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

### Enable API access in MT5

1. Open the MT5 terminal and log in to your IC Markets account.
2. **Tools → Options → Expert Advisors** → tick **"Allow algorithmic trading"**.
3. Make sure the **"Algo Trading"** button in the top toolbar is green/enabled.
4. Keep the terminal **running and logged in** while the bot runs — the Python
   API attaches to that terminal.

---

## 3. Find your IC Markets MT5 server name

The server name must match **exactly** (it's case-sensitive).

- In the MT5 terminal: **File → Login to Trade Account** → the **Server**
  dropdown shows the exact string.
- Or check the welcome email IC Markets sent when you opened the account.

Typical values:

| Account type | Example server names |
|--------------|----------------------|
| Demo         | `ICMarketsSC-Demo`, `ICMarkets-Demo02` |
| Live         | `ICMarketsSC-Live01`, `ICMarketsSC-Live02`, `ICMarketsEU-Live` |

Your exact name depends on the IC Markets entity (SC, EU, Global) your account
sits under — always copy it from the terminal.

---

## 4. Configure `.env`

Credentials are **never hardcoded**. Copy the template and fill it in:

```bash
cp .env.example .env
```

Minimum to set:

```ini
MT5_LOGIN=12345678
MT5_PASSWORD=your-password
MT5_SERVER=ICMarketsSC-Demo
SYMBOL=XAUUSD
TIMEFRAME=H1
TRADE_MODE=demo
```

### About the symbol suffix

IC Markets usually lists gold as plain **`XAUUSD`**, but some account types use a
suffix like **`XAUUSD.a`** or **`XAUUSD.i`**. If the bot can't find your symbol it
prints every gold-like symbol on your account so you can copy the exact name into
`SYMBOL`. The connection check (next step) shows you this.

---

## 5. Pre-flight connection check (do this first)

This only **reads** — it never places an order:

```bash
python check_connection.py
```

It confirms: login works, the symbol resolves (with its real suffix and lot
specs), data flows, and indicators/signal compute. Fix any reported issue before
running the bot.

---

## 6. Run on demo

```bash
python bot.py
```

In demo mode the bot trades on your **demo account**. Extra safety net: if it
detects `TRADE_MODE=demo` but you're logged into a **real** account, it switches
to **dry-run** (signals are logged, **no orders sent**).

Watch `logs/bot.log` (and the console). Let it run across several signals and
confirm the behaviour looks right **before** considering live.

---

## 7. Going live (only after demo!)

Live trading is intentionally hard to enable by accident. You must set **both**:

```ini
TRADE_MODE=live
LIVE_CONFIRM=YES_I_UNDERSTAND
```

If `LIVE_CONFIRM` is missing, the bot refuses to start. When live, it logs a clear
**"LIVE TRADING IS ENABLED. Real money is at risk."** warning on every startup.

> Start with the **smallest** risk and a small balance. Re-read the disclaimer.

---

## 8. Backtest before trusting it

Reuses the exact same entry/exit/sizing logic as the live bot.

```bash
# Using live MT5 history (Windows, terminal open):
python backtest.py --bars 5000

# Fully offline from a CSV (any OS) — columns: time,open,high,low,close,tick_volume
python backtest.py --csv data/xauusd_h1.csv --tick-value 1.0 --tick-size 0.01
```

It reports net profit, return %, trades, win rate, profit factor, max drawdown and
average win/loss. Fills are approximated from each bar's high/low and, when both
stop and target are touched in one bar, the **stop is assumed first** (pessimistic).
**Backtest results do not guarantee live performance — forward-test on demo.**

---

## 9. The strategy (mechanical, all configurable)

**Trend filter**
- Long allowed only when `SMA50 > SMA200` (bullish).
- Short allowed only when `SMA50 < SMA200` (bearish).

**Entries**
- Long: bullish trend **and** RSI(14) crosses **up** through 30.
- Short: bearish trend **and** RSI(14) crosses **down** through 70.

**Exits**
- Stop loss: `1.5 × ATR` (default) or the recent swing low/high (`SL_METHOD=swing`).
- Take profit: `RISK_REWARD ×` the stop distance (default **1:2**).
- A reverse signal **closes the opposite position**.
- **No duplicate positions** in the same direction.

All entry logic lives in `strategy.py`; all indicators in `indicators.py`.

---

## 10. Risk management (enforced)

- **Max 1% of balance risked per trade** — lot size is derived from the *actual*
  stop distance and IC Markets' per-symbol tick value, then snapped to the broker's
  min/step/max lot. If even the minimum lot would exceed 1%, the trade is **skipped**
  rather than over-risked.
- **Margin check** before every order (`order_calc_margin`) — respects your account
  leverage; no over-leveraging.
- **Daily loss limit** (`DAILY_LOSS_LIMIT`, default 3%) — once hit, **no new trades**
  open until the next calendar day. Existing positions are still managed.
- **Spread guard** (optional `MAX_SPREAD_POINTS`) — skip entries when spread blows out.

---

## 11. Adjust strategy / risk parameters

Everything is in `.env` — no code changes needed. The most common ones:

| Setting | Meaning | Default |
|---|---|---|
| `SYMBOL` / `TIMEFRAME` | instrument & candle size (`M15`,`H1`,`H4`,`D1`…) | `XAUUSD` / `H1` |
| `TRADE_HOUR_START`/`END` | trading window (server time, 24h) | `00:00`–`23:59` |
| `RISK_PER_TRADE` | fraction of balance risked per trade | `0.01` (1%) |
| `RISK_REWARD` | take-profit multiple of stop distance | `2.0` |
| `DAILY_LOSS_LIMIT` | daily pause threshold | `0.03` (3%) |
| `SL_METHOD` | `atr` or `swing` | `atr` |
| `ATR_MULTIPLIER` / `SWING_LOOKBACK` | stop sizing | `1.5` / `10` |
| `SMA_FAST`/`SMA_SLOW`/`RSI_PERIOD` | indicator periods | `50`/`200`/`14` |
| `RSI_OVERSOLD`/`RSI_OVERBOUGHT` | RSI cross levels | `30`/`70` |
| `POLL_SECONDS` | loop interval | `30` |
| `MAGIC_NUMBER` | tags this bot's orders | `990011` |

---

## 12. Optional Telegram alerts

Get a bot token from **@BotFather** and your chat id (e.g. from **@userinfobot**),
then in `.env`:

```ini
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
```

You'll get a message on each trade open/close. Alert failures never interrupt
trading — they're just logged.

---

## 13. File map

| File | Purpose |
|---|---|
| `config.py` | loads & validates all settings from `.env` |
| `mt5_client.py` | MT5 connect / reconnect / data / orders |
| `indicators.py` | SMA, RSI, ATR, swing high/low (via `ta`) |
| `strategy.py` | signal generation + stop/target logic |
| `risk.py` | lot sizing, margin check, daily loss guard |
| `bot.py` | the main live/demo loop |
| `backtest.py` | historical simulation |
| `check_connection.py` | read-only pre-flight test |
| `notifier.py` | optional Telegram alerts |
| `logger.py` | console + rotating file logging |

---

## 14. Troubleshooting

- **`initialize() failed`** — MT5 terminal not running/logged in, "Algo Trading"
  disabled, or wrong `MT5_SERVER`. Set `MT5_TERMINAL_PATH` if you have multiple
  terminals installed.
- **Symbol not found** — run `check_connection.py`; copy the exact suffixed name it
  lists into `SYMBOL`.
- **"min lot would risk more than allowed"** — your stop is tight and/or balance is
  small; the bot correctly refuses to over-risk. Increase balance, widen the stop,
  or (knowingly) raise `RISK_PER_TRADE`.
- **Orders rejected (retcode)** — market closed, insufficient margin, or invalid
  stops too close to price; check the logged retcode/comment.
