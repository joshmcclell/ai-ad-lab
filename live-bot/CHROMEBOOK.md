# Running this bot on a Chromebook (backtest & validate)

You **cannot** live-trade from ChromeOS — the `MetaTrader5` package needs the
Windows MT5 terminal (see README §3). But you **can** do all the important work
for free on your Chromebook: run the logic self-tests and backtest the strategy
on historical 1-minute data. Do that first; only pay for a Windows VPS to go
live once you're happy.

This guide uses the Chromebook's built-in **Linux (Crostini)** container. No
Windows, no MT5 required.

---

## 1. Turn on Linux on your Chromebook

1. **Settings → Advanced → Developers → Linux development environment → Turn on.**
   (On some models: Settings → "About ChromeOS" isn't it — look under
   *Developers*.) Accept the defaults; it downloads a small Debian container.
2. When it finishes, a **Terminal** app appears. Open it — you now have a normal
   Linux shell.

> If you don't see the Linux option, your Chromebook may be too old or managed
> by a school/work admin. In that case use the Windows-VPS route in README §6
> for everything, or ask the admin to enable Linux.

---

## 2. Install Python and the bot's dependencies

In the Linux Terminal:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# get the code onto the Chromebook (clone your repo, or copy the trading-bot folder)
git clone <your-repo-url>
cd ai-ad-lab/trading-bot          # adjust if your path differs

# isolated environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# only the cross-platform deps are needed for backtesting:
pip install pandas numpy pandas-ta python-dotenv
# optional, for downloading data from Yahoo:
pip install yfinance
```

`MetaTrader5` will **not** install here — that's expected and fine. It's only
needed for live trading on Windows.

---

## 3. Prove the logic works (offline, instant)

```bash
python selftest.py
```

You should see all checks pass — including that lot size never exceeds 0.05
across $1k–$1M balances and the −2% daily-loss guard trips correctly.

---

## 4. Get 1-minute data for the backtest

Use the included `fetch_data.py` helper. Three ways:

**A) Instant offline test data (no internet) — start here:**
```bash
python fetch_data.py --synthetic --days 7 --out data/xau_sample.csv
```
This makes a realistic random-walk dataset so you can confirm the whole
pipeline runs. (It's noise, so don't read anything into the P/L — it just
proves the machinery.)

**B) Free real-ish gold data from Yahoo (last ~7 days only):**
```bash
python fetch_data.py --yahoo --out data/gold_1m.csv
```
This pulls gold **futures** (GC=F) as a close proxy for spot XAUUSD — good
enough to see the strategy react to genuine price action. Yahoo caps 1-minute
history at roughly 7 days.

**C) Real XAUUSD history you export yourself (best for serious backtests):**
- Free, multi-year: download from **Dukascopy Historical Data Feed**
  (dukascopy.com → Tools → Historical Data Feed), choose *XAU/USD*, *1 Min*,
  *CSV*. Then convert it:
  ```bash
  python fetch_data.py --convert ~/Downloads/XAUUSD_Candlestick_1_M.csv \
                       --out data/xau_1m.csv
  ```
- Or, on any Windows machine with MT5: open the M1 chart, scroll back to load
  history, then export and copy the CSV to your Chromebook and `--convert` it.

The converter auto-detects common column names (Dukascopy's "Gmt time",
MT5's Date/Time, etc.).

---

## 5. Run the backtest

```bash
python backtest.py --csv data/xau_sample.csv --balance 1000
# or your real data:
python backtest.py --csv data/xau_1m.csv --balance 1000 --spread 0.20
```

You'll get a report (trades, win rate, profit factor, net P/L, **max lot used**)
and a full per-trade CSV at `logs/backtest_trades.csv`. Open that CSV in the
ChromeOS Files app or Google Sheets to inspect every entry/exit.

**Tuning loop:** edit numbers in `config.py` (risk %, ATR multiplier, RSI bands,
ATR minimum, candle-confirmation on/off), re-run the backtest, compare. Because
the backtester and the live bot share the exact same `strategy.evaluate()`, what
you tune here is what you'll get live.

---

## 6. When you're ready to go live

Live trading still needs Windows + MT5. The standard path:
1. Rent a small **Windows VPS** (~$5–15/mo; IC Markets may offer a free one to
   qualifying clients — ask their support).
2. On the VPS: install MT5 (IC Markets), Python, `pip install -r requirements.txt`
   (now `MetaTrader5` installs), copy your tuned `config.py` + a `.env`.
3. Connect to the VPS from your Chromebook with the **Chrome Remote Desktop**
   app or any RDP client, then follow README §4 (demo first, then `--live`).

A VPS also means the bot runs 24/7 without your Chromebook staying awake —
which is what you want for a 1-minute scalper anyway.

---

## TL;DR

```bash
# one-time
sudo apt install -y python3 python3-pip python3-venv git
python3 -m venv .venv && source .venv/bin/activate
pip install pandas numpy pandas-ta python-dotenv yfinance

# every session
python selftest.py                                   # logic checks
python fetch_data.py --synthetic --days 7 --out data/x.csv   # or --yahoo / --convert
python backtest.py --csv data/x.csv --balance 1000   # results + logs/backtest_trades.csv
```
