# Going live from a Chromebook — running the bot with MT5

Live trading needs the **Windows MetaTrader 5 terminal**, which ChromeOS can't
run natively. The reliable way to use the bot from your Chromebook is to run
MT5 + the bot on a small **cloud Windows PC (a "VPS")** and control it from your
Chromebook over Remote Desktop. Your Chromebook becomes the screen; the VPS does
the trading 24/7, even when your laptop is closed.

> Validate the strategy first for free on your Chromebook (see CHROMEBOOK.md).
> Only rent a VPS once your backtest + demo look good.

---

## Part A — Get a Windows VPS

You need a **Windows** VPS near your broker's servers for low latency. Options:

- **Broker / Forex VPS:** ForexVPS.net, Cloudzy, FXVM, Beeks (~$7–12/mo, made
  for MT5). IC Markets also offers a **free VPS** to clients who meet their
  equity/volume minimums — ask IC Markets support; it's the cheapest route.
- **General cloud:** Contabo (cheap Windows), Vultr / AWS Lightsail / Azure /
  Google Cloud (hourly, Windows license included).

When you create it, choose **Windows Server 2019/2022**, the smallest plan with
~2 GB+ RAM is plenty. Save the VPS's **IP address, username, and password**.

---

## Part B — Connect to the VPS from your Chromebook

Two easy ways — pick one:

1. **Microsoft Remote Desktop (Android app).** Most Chromebooks run Android
   apps. Install "Microsoft Remote Desktop" ("RD Client") from the Play Store,
   add a PC with your VPS IP, log in with the VPS username/password.
2. **Chrome Remote Desktop.** On the VPS, install Chrome + the Chrome Remote
   Desktop *host*, sign in with a Google account, set a PIN; then open
   `remotedesktop.google.com/access` from your Chromebook.

You now see a Windows desktop inside your Chromebook.

---

## Part C — Set up MT5 + the bot ON the VPS

Do all of this inside the Remote Desktop window (it's a normal Windows PC):

1. **Install MT5:** download the **IC Markets MetaTrader 5** installer from IC
   Markets' site, install it, and log in with your account
   (login / password / server, e.g. `ICMarketsSC-Demo`).
   - In MT5: **Tools → Options → Expert Advisors → "Allow algorithmic trading"** ✔
   - Make sure the toolbar **Algo Trading** button is green.

2. **Install Python 3.10+:** get it from python.org. On the first installer
   screen tick **"Add python.exe to PATH"**.

3. **Get the bot onto the VPS:** install Git for Windows (or just download your
   repo as a ZIP and extract it). Open **Command Prompt** (or PowerShell):
   ```bat
   git clone <your-repo-url>
   cd ai-ad-lab\trading-bot
   pip install -r requirements.txt
   ```
   On Windows, `MetaTrader5` installs correctly here (unlike on ChromeOS).

4. **Configure your login:** copy `.env.example` to `.env` and edit it
   (Notepad is fine):
   ```bat
   copy .env.example .env
   notepad .env
   ```
   Fill in `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, keep `DEMO_MODE=true`.

5. **Find your gold symbol name** (IC Markets sometimes uses a suffix):
   ```bat
   python bot.py --list-symbols
   ```
   Put the exact name (e.g. `XAUUSD` or `XAUUSD.a`) into `.env` as `MT5_SYMBOL`.

---

## Part D — Test, then go live (same as README §4)

```bat
python bot.py --once     :: one evaluation against your DEMO account
python bot.py            :: continuous loop on DEMO
```
Leave it running across a London session, then check `logs\trades.csv`.

When you're satisfied on demo, switch to a **live** IC Markets account in MT5,
update `.env` (or use `--live`), and:
```bat
python bot.py --live
```
The bot prints a **LIVE ACCOUNT** banner before trading. Start small — sizing
adapts to your balance and is hard-capped at 0.05 lots.

> **Keep it running 24/7:** because the VPS stays on, the bot keeps trading the
> London session every day without your Chromebook. To survive a VPS reboot,
> you can later wrap `python bot.py` in a Windows Task Scheduler task or a `.bat`
> file in the Startup folder — but get comfortable running it by hand first.

---

## Alternative: fully local on the Chromebook (advanced, fragile)

If you specifically want everything on the Chromebook with **no VPS**, you'd run
the Windows MT5 terminal and a **Windows** build of Python under **Wine** in the
Linux (Crostini) container, then `pip install MetaTrader5` *inside that Wine
Python* and run the bot with it so it can attach to the terminal in the same
Wine prefix.

Be aware:
- **It does not work on ARM Chromebooks** (many Chromebooks use ARM chips); Wine
  there can't run x86 Windows binaries without heavy emulation.
- Even on Intel/AMD Chromebooks it's flaky, and a crash means no trades fire.
- It still can't trade while the laptop is asleep.

For real money, use the VPS. The Wine route is for experimentation only, and is
not something this project officially supports.
