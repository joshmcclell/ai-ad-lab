# Free setup: run MT5 + the bot on an Intel/AMD Chromebook via Wine

This runs the **Windows** MetaTrader 5 terminal and a **Windows** build of Python
*inside* your Chromebook's Linux container using **Wine** — no VPS, no cost. The
bot then talks to MT5 exactly like it would on a real Windows PC.

**Only works on `x86_64` (Intel/AMD) Chromebooks.** Check with `uname -m`.

> ⚠️ Two honest warnings:
> 1. **Use a DEMO account.** Wine can crash; if it dies mid-trade no orders
>    fire and a position could sit unmanaged. Never run real money this way
>    until you've watched it behave on demo for a long time.
> 2. It only trades while your Chromebook is **on and awake**. That's fine for
>    the London session (08:00–16:00) if you're at the machine. For 24/7 you'd
>    eventually want the VPS in GO_LIVE.md — but start here, free.

---

## 1. Turn on Linux and open the Terminal

Settings → Advanced → Developers → **Linux development environment → Turn on.**
Open the **Terminal** app it installs. Confirm your chip:

```bash
uname -m        # must print: x86_64
```

---

## 2. Install Wine

```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install -y wine wine64 wine32 winbind cabextract winetricks
```

If `wine` reports it's too old later, install the newer WineHQ build instead —
but the Debian package is usually fine. Initialise Wine (creates `~/.wine`):

```bash
winecfg
```

A settings window opens. Set **Windows Version → Windows 10**, click OK. If it
complains about "Mono"/"Gecko", click **Install** on each.

---

## 3. Install the IC Markets MT5 terminal under Wine

1. In the Chrome browser, download the **MetaTrader 5** desktop installer from
   **IC Markets** (their website → Trading Platforms → MetaTrader 5 → Windows).
   It saves to `~/Downloads` (Linux files share: drag it into the *Linux files*
   folder in the ChromeOS Files app if needed).
2. Run the installer with Wine:
   ```bash
   cd ~/Downloads
   wine icmarkets5setup.exe        # use the actual filename you downloaded
   ```
   Click through the installer. When it finishes, MT5 launches.
3. **Log into your DEMO account** (login / password / server, e.g.
   `ICMarketsSC-Demo`).
4. In MT5: **Tools → Options → Expert Advisors → "Allow algorithmic trading"** ✔,
   and click the toolbar **Algo Trading** button so it's green. Leave MT5 open.

The terminal installs to roughly:
`~/.wine/drive_c/Program Files/MetaTrader 5 IC Markets/terminal64.exe`
You can relaunch it anytime with:
```bash
wine "C:/Program Files/MetaTrader 5 IC Markets/terminal64.exe" &
```

---

## 4. Install Windows Python *inside* Wine

The bot's `MetaTrader5` package must run under the **same Wine** as the terminal.

```bash
cd ~/Downloads
wget https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
wine python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
```

Verify Wine's Python works:
```bash
wine python --version        # should print Python 3.11.9
```

Install the bot's libraries into **Wine's** Python:
```bash
wine python -m pip install --upgrade pip
wine python -m pip install MetaTrader5 pandas numpy python-dotenv
# pandas-ta is optional — the bot has built-in indicator fallbacks. Try it,
# but if it fails to install under Wine, just skip it:
wine python -m pip install pandas-ta || echo "skipping pandas-ta (optional)"
```

---

## 5. Get the bot and configure it

```bash
cd ~
git clone <your-repo-url>
cd ai-ad-lab/trading-bot
cp .env.example .env
nano .env       # fill MT5_LOGIN / MT5_PASSWORD / MT5_SERVER ; keep DEMO_MODE=true
```

Find your exact gold symbol name (run the bot under Wine's Python):
```bash
wine python bot.py --list-symbols
```
Put the result (e.g. `XAUUSD` or `XAUUSD.a`) into `.env` as `MT5_SYMBOL`.

---

## 6. Run it (on demo)

Make sure the MT5 terminal from step 3 is **open and logged in**, then:

```bash
wine python bot.py --once     # single evaluation — proves the connection works
wine python bot.py            # continuous loop during the London session
```

Trades are logged to `logs/trades.csv`. Stop with **Ctrl-C**.

> Remember: run these with `wine python ...`, NOT plain `python ...`. Plain
> `python` is the Linux Python, which can't reach the Windows MT5 terminal — it's
> only for `selftest.py` and the backtester.

---

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| `wine: command not found` | Re-run step 2; open a new Terminal tab. |
| winecfg / MT5 window won't appear | Crostini GUI hiccup — reboot the container: `sudo reboot` (or restart Linux from Settings), try again. |
| `MT5 initialize() failed` | The terminal isn't running/logged in, or Algo Trading is off. Open MT5 first (step 3), then run the bot. |
| `Symbol 'XAUUSD' not found` | Run `wine python bot.py --list-symbols` and copy the exact name into `.env`. |
| `pandas-ta` won't install | Skip it — the bot computes EMA/RSI/ATR itself without it. |
| Bot can't connect but terminal is open | Make sure you used `wine python` (Wine's Python), not the Linux `python`. Both must share the same `~/.wine` prefix. |
| Everything is very slow | Wine + MT5 is heavy; close other tabs/apps. A 1-minute timeframe is forgiving — it only needs to act once a minute. |

If you get stuck, copy the exact error text — most failures are one of the rows
above.
