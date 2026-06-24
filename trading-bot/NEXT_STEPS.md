# Where this project is up to (status + next steps)

A running status note so you (or a fresh chat session) can pick up without
re-deriving everything. Everything below is committed to the
`claude/clever-wright-k6xing` branch.

## What works right now
- Bot runs on the Chromebook via **Wine** (MT5 + Windows Python), connected to
  IC Markets demo. See WINE_SETUP.md.
- **Telegram alerts** working (open/close/error/daily-loss). See ALERTS.md.
- Backtester + data tools run on native Linux `python3` (pandas/numpy via
  `sudo apt install python3-pandas python3-numpy python3-dotenv`).

## Current settings (in config.py / .env)
- `FIXED_LOT=0.10` -> trades exactly 0.10 lots every trade (overrides 0.05 cap).
- `risk_reward_ratio = 0.4` + `sl_atr_multiplier = 1.5` -> HIGH WIN-RATE preset
  (close TP, wide stop). Spread filter `max_spread_frac_of_tp = 0.33`.
- `TRADE_24H=true`, `ALLOW_MIN_LOT=true`.

## The honest finding so far
Two backtests (synthetic + 1 day real) both show the high-win-rate config
**losing money** (profit factor 0.37 and 0.08). Lesson, proven with numbers:
**a high win rate does NOT mean profit.** The metric that matters is
**profit factor** (>1.0 = profitable). Stop tuning win rate; tune profit factor.

## NEXT STEPS (in priority order)

### 1. Get a REAL, large backtest (do this first)
Easiest - straight from MT5 (MT5 open + logged in):
```bash
WINEDEBUG=-all wine python backtest.py --from-mt5 --days 90
```
Alternative - Dukascopy CSV (must set BOTH From and To dates to span months):
```bash
python3 fetch_data.py --convert ~/XAU-USD_1Minute_BID_*.csv --out data/xau_real.csv
python3 backtest.py --csv data/xau_real.csv --balance 1000
```
Goal: hundreds+ of trades. Read **Profit factor**, not win rate.

### 2. Fix the live P&L reporting bug (parked)
Live trades log `WIN pnl=0.00` even when balance drops - the realised P/L
lookup returns 0 and the WIN/LOSS label is wrong. Affects the terminal log,
logs/trades.csv, AND the Telegram alerts. Fix: compute P/L from the real
closed deal (or balance delta) and only label WIN when pnl > 0.
(The BACKTESTER's P/L is correct - it's a separate code path - so backtest
numbers are already trustworthy.)

### 3. Make the backtester honour FIXED_LOT (parked)
backtest.py currently always uses risk-based sizing (calculate_lot_size), so it
does NOT reflect FIXED_LOT=0.10. Win rate / profit factor are ~unaffected, but
the £ P/L in the report won't match live. Wire fixed_lot_size into backtest.py.

### 4. Then tune for profit factor > 1.0
Once we can measure on real data: try a balanced RR (e.g. 1.5-2.0), add a
trailing stop / move-to-break-even, tighten entries (session, spread), and
re-backtest each change. Keep only changes that raise profit factor on
out-of-sample data. Do NOT go live until a configuration is profitable on
real data AND on a few weeks of demo.

## Command cheat-sheet
```bash
# LIVE / DEMO (needs MT5 open, run with Wine python):
WINEDEBUG=-all wine python bot.py            # demo loop
WINEDEBUG=-all wine python bot.py --once     # single check
WINEDEBUG=-all wine python bot.py --test-alert

# BACKTEST / DATA (native python3, no MT5 needed unless --from-mt5):
WINEDEBUG=-all wine python backtest.py --from-mt5 --days 90   # real data via MT5
python3 backtest.py --csv data/xau_real.csv --balance 1000
python3 selftest.py
```
```bash
# update code on the Chromebook:
cd ~/ai-ad-lab && git pull origin claude/clever-wright-k6xing && cd trading-bot
```
```
Reminder: keep DEMO_MODE=true. The current config is high-risk and unproven.
```
