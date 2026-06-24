# Trade alerts on your phone (Telegram)

Get an instant message when the bot **opens** a trade, **closes** one, hits the
**daily-loss limit**, or **errors** — so you can watch it on demo without sitting
at the terminal. Free, and it needs no extra Python packages.

## 1. Make a Telegram bot (1 minute)
1. In Telegram, search for **@BotFather** and start it.
2. Send **/newbot**, follow the prompts, pick a name.
3. BotFather replies with a **token** like `8123456789:AAH...xyz`. Copy it.

## 2. Let the bot message you
Search for the bot you just made (the username you chose) and send it any
message, e.g. **hi**. (A bot can't message you until you've messaged it first.)

## 3. Find your chat ID
Put the token in `.env` first, then run the helper:
```bash
nano .env        # set TELEGRAM_BOT_TOKEN=... and ALERTS=true
WINEDEBUG=-all wine python bot.py --telegram-setup
```
It prints something like:
```
Found these chat IDs — put the right one in .env as TELEGRAM_CHAT_ID:
   CHAT_ID = 123456789   (Josh)
```
Copy that number into `.env` as `TELEGRAM_CHAT_ID`.

## 4. Your `.env` alert section should look like
```ini
ALERTS=true
TELEGRAM_BOT_TOKEN=8123456789:AAH...xyz
TELEGRAM_CHAT_ID=123456789
```

## 5. Test it
```bash
WINEDEBUG=-all wine python bot.py --test-alert
```
You should get a Telegram message within a second or two. If not, the terminal
prints why (usually a wrong token or chat ID, or `ALERTS` not set to `true`).

## What you'll receive
- 🤖 **Started** — account, balance, demo/live, symbol.
- 🟢 **OPEN** — direction, lot, entry, SL, TP, money at risk.
- ✅/❌ **CLOSED** — result, P/L, new balance.
- ⛔ **Daily loss limit hit** — trading paused for the day.
- ⚠️ **Entry failed / error** — so you know if something went wrong.

Alerts run in a background thread and never block or crash the trading loop —
if Telegram is unreachable, the bot just logs a warning and keeps trading.
