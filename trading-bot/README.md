# XAU/USD 1-Minute Scalping Bot — MetaTrader 5 / IC Markets

A fully rule-based (no ML, no black boxes) scalping bot for **Gold vs US Dollar
(XAUUSD)** on the **1-minute** timeframe, built for **MetaTrader 5** with
**IC Markets**. It connects to your MT5 terminal, computes its own indicators,
sizes every position from your live account balance, and **never exceeds 0.05
lots**.

> ⚠️ **Risk warning.** Trading leveraged gold is high-risk. This software is for
> education and testing. Run it on a **demo account** until you fully understand
> its behaviour. Past backtest results do not predict future returns.

> 💻 **On a Chromebook / no Windows?** Backtest for free on ChromeOS's Linux
> container — see **[CHROMEBOOK.md](CHROMEBOOK.md)**. To trade **live** from a
> Chromebook, run MT5 + the bot on a cloud Windows VPS and control it via Remote
> Desktop — full walkthrough in **[GO_LIVE.md](GO_LIVE.md)**.

---

## 1. What's in the box

| File | Purpose |
|------|---------|
| `config.py` | **All settings in one place** — credentials, indicator periods, risk %, ATR multiplier, lot limits, session hours, news buffer. |
| `indicators.py` | EMA(20/50), RSI(7), ATR(5) and candle patterns (engulfing / pin bar). Uses `pandas-ta` if present, with transparent manual fallbacks. |
| `strategy.py` | The rule engine. Turns candles → `LONG` / `SHORT` / `NONE` with SL & TP. Shared by live bot and backtester. |
| `risk.py` | **Position sizing** (risk %, SL distance, 0.05 cap) + the **daily-loss circuit breaker**. |
| `mt5_client.py` | Defensive wrapper over the `MetaTrader5` API: connect, fetch data, read specs, place/close orders, margin checks. |
| `trade_logger.py` | Append-only **CSV trade log** + console logging. |
| `bot.py` | The **live / demo loop** with a hard demo-mode safety gate. |
| `backtest.py` | **Backtester** over historical 1m data (from MT5 or a CSV). |
| `selftest.py` | Offline checks (lot cap, daily-loss guard, R:R) — no terminal needed. |

---

## 2. The strategy, precisely

A signal fires **only when every filter agrees** on the just-closed 1m candle.

**Entry — LONG**
1. **Trend:** EMA20 > EMA50 **and** close > both EMAs.
2. **Momentum:** 40 < RSI(7) < 70 (not overbought).
3. **Volatility:** ATR(5) ≥ 0.15 (enough movement to scalp).
4. **Candle:** bullish engulfing **or** bullish pin bar (toggleable).
5. **Session:** 08:00–16:00 London (UTC+1), auto-tracking GMT/BST.
6. **News:** skip ±15 min around configured high-impact events.

**Entry — SHORT** — the mirror image (EMA20 < EMA50, close < both EMAs,
30 < RSI < 60, bearish candle).

**Exit / risk**
- **Stop loss:** `1.2 × ATR` from entry.
- **Take profit:** `1.5 × stop distance` (1 : 1.5 reward-to-risk).
- **Risk per trade:** 1% of live balance (adjustable in `config.py`).
- **Max daily loss:** stop all new trades after −2% on the day.
- **Max open trades:** 1 at a time.

Everything above is a single number in `config.py` — change it and restart.

---

## 3. Setup

### 3.1 Install MetaTrader 5 + the Python package

The official `MetaTrader5` package is **Windows-only** (it talks to the desktop
terminal). Use Windows, a Windows VM, or Wine.

1. Install the **MT5 terminal** from IC Markets and log into your account.
2. In the terminal: **Tools → Options → Expert Advisors → "Allow algorithmic
   trading"** ✔, and on the toolbar make sure **Algo Trading** is green.
3. Install Python 3.10+ and the dependencies:

```bash
pip install -r requirements.txt
```

> On Linux/macOS `MetaTrader5` is skipped automatically (see the marker in
> `requirements.txt`). You can still run `selftest.py` and the CSV backtester.

### 3.2 Configure your IC Markets login

```bash
cp .env.example .env
```

Edit `.env`:

```ini
MT5_LOGIN=12345678
MT5_PASSWORD=your-password
MT5_SERVER=ICMarketsSC-Demo      # EXACT string from your terminal
MT5_SYMBOL=XAUUSD                # or XAUUSD.a etc. — see below
DEMO_MODE=true                   # keep true until demo-tested
```

**Finding your server name:** MT5 → *File → Login to Trade Account* — the
drop-down shows it (e.g. `ICMarketsSC-Demo`, `ICMarketsSC-Live01`).

**Finding the gold symbol:** most accounts use `XAUUSD`; some use a suffix. Run:

```bash
python bot.py --list-symbols
```

and copy the exact name into `MT5_SYMBOL`.

---

## 4. How to run: backtest → demo → live

### Step 1 — Backtest (prove the logic on history)

From MT5 history (terminal running):
```bash
python backtest.py --from-mt5 --days 30 --balance 1000
```
From a CSV you exported (no terminal needed):
```bash
python backtest.py --csv data/xauusd_m1.csv --balance 1000
```
You get a report (trades, win rate, profit factor, net P/L, max lot) and a full
per-trade CSV at `logs/backtest_trades.csv`. By default the backtester does not
enforce the London-session clock (so tz-naive data still produces signals); set
`check_time=True` in `backtest.py` to include it.

> Offline sanity check that needs nothing installed but pandas/numpy:
> ```bash
> python selftest.py
> ```

### Step 2 — Demo test (real fills, fake money)

With `DEMO_MODE=true` and a **demo** login, run:
```bash
python bot.py --once      # one evaluation, then exit (smoke test)
python bot.py             # continuous loop
```
If `DEMO_MODE=true` but the account is live, the bot **refuses to trade** and
exits. Let it run across a London session and inspect `logs/trades.csv`.

### Step 3 — Live (real money)

Only after you're satisfied on demo:
```bash
# either set DEMO_MODE=false in .env, or pass --live for one run:
python bot.py --live
```
The bot prints a **LIVE ACCOUNT** banner. Start with the smallest balance you're
comfortable with — sizing adapts automatically.

---

## 5. How lot sizing works (and why it stays ≤ 0.05)

Computed fresh on **every** signal from the **live balance** (`risk.py`):

```
1. money_at_risk = balance × risk_per_trade_pct / 100      # e.g. $1000 × 1% = $10
2. loss_per_lot  = (sl_distance / tick_size) × tick_value  # real broker specs
                   # offline fallback: sl_distance × 100  (1 lot = 100 oz)
3. raw_lot       = money_at_risk / loss_per_lot
4. lot           = floor(raw_lot to 0.01 step)             # round DOWN → never over-risk
5. lot           = min(lot, 0.05)                          # ← HARD 0.05 CEILING
6. if lot < 0.01 → skip the trade                          # don't silently over-risk
```

Worked examples (SL distance shown in USD; XAUUSD 1 lot = 100 oz):

| Balance | Risk 1% | SL dist | raw lot | Final lot | Note |
|--------:|--------:|--------:|--------:|----------:|------|
| $100    | $1      | 2.0     | 0.005   | **skipped** | below 0.01 min → no trade |
| $500    | $5      | 1.5     | 0.033   | **0.03**    | floored to step |
| $1,000  | $10     | 1.0     | 0.100   | **0.05**    | capped at ceiling |
| $1,000,000 | $10,000 | 1.0  | 100.0   | **0.05**    | still capped at ceiling |

The cap in **step 5 is unconditional** — no balance can ever push size past
0.05. This is verified by `selftest.py` across $1k–$1M. Live, the same maths
uses the broker's real `tick_size`/`tick_value` from `symbol_info()`, so the
risk figure is exact for IC Markets XAUUSD, and a **margin check** runs before
every order.

To change the risk, edit one line in `config.py`:
```python
risk_per_trade_pct: float = 1.0   # → 0.5 for half-risk, 2.0 for double, etc.
```

---

## 6. Spread, slippage & scalping best practice for XAUUSD

Scalping gold on M1 lives and dies on transaction costs — the TP is small, so a
wide spread eats your edge.

- **Use a Raw/ECN account.** IC Markets *Raw Spread* gold typically runs
  ~0.02–0.15 spread + ~$3.5/side commission ($7 round-turn per lot), far better
  than a "standard" account's ~0.20–0.35 marked-up spread. The backtester models
  both: tune `--spread` and `commission_per_lot` in `backtest.py`.
- **Trade liquid hours only.** The London window (08:00–16:00) and the
  London/NY overlap give the tightest spreads. Avoid the 22:00–01:00 rollover
  when spreads balloon. The session filter enforces this.
- **Expect slippage on entries/exits.** Market orders fill at the touch; the bot
  allows `deviation_points` (default 20) of slippage and the backtester adds a
  `slippage_price` cushion so results stay honest.
- **Mind the broker stop level.** IC Markets enforces a minimum SL/TP distance
  (`trade_stops_level`); the bot reads it and nudges SL/TP out if your
  ATR-based stop is tighter than allowed.
- **News kills scalps.** High-impact releases (NFP, US CPI, FOMC) spike the
  spread and gap price through stops. Populate `news_events` in `config.py` (or
  wire a calendar feed) so the bot stands aside ±15 min.
- **One trade at a time, capped daily loss.** Both are enforced — don't disable
  them to "make back" a loss. Let the −2% guard end the day.
- **Backtest with realistic costs**, then forward-test on demo for at least a
  couple of weeks before risking real money. M1 backtests are sensitive to
  spread/slippage assumptions — be conservative.

---

## 7. Error handling built in

- **Connection:** clear messages for failed `initialize`/`login`, with hints
  (algo trading enabled? server/login correct?).
- **Missing data / closed market:** raises a descriptive error instead of acting
  on empty candles.
- **Symbol not found:** tells you to run `--list-symbols` (handles `.a` suffixes).
- **Invalid orders:** checks the broker stop level and filling mode; surfaces the
  exact `retcode` on rejection.
- **Margin:** `order_calc_margin` is checked against free margin before sending.
- **Loop resilience:** the live loop catches per-iteration errors and keeps
  running rather than crashing.

---

## 8. Quick reference

```bash
python selftest.py                         # offline logic checks
python bot.py --list-symbols               # find your XAUUSD symbol name
python backtest.py --csv data/xau.csv      # backtest on a CSV
python backtest.py --from-mt5 --days 30    # backtest on MT5 history
python bot.py --once                       # single demo evaluation
python bot.py                              # demo loop (DEMO_MODE=true)
python bot.py --live                       # live trading (deliberate)
```

All trades land in `logs/trades.csv`:
`open_time, close_time, symbol, direction, lot, entry_price, stop_loss,
take_profit, exit_price, atr, money_at_risk, result, pnl, balance_after,
order_ticket, comment`.
