"""
alerts.py
=========
Push notifications for the bot via **Telegram** — free, instant, and works on
your phone and Chromebook. Zero extra Python packages (uses the standard
library), so it installs nowhere and can't break the trading loop: every send
runs in a background thread and swallows its own errors.

Setup (see ALERTS.md for the walkthrough):
  1. In Telegram, message @BotFather -> /newbot -> copy the bot TOKEN.
  2. Message your new bot once (say "hi") so it can reach you.
  3. Run:  wine python bot.py --telegram-setup    (prints your CHAT ID)
  4. Put TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env, set ALERTS=true.

Then test:  wine python bot.py --test-alert
"""

from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request

_API = "https://api.telegram.org/bot{token}/{method}"


class Notifier:
    """Sends short text alerts to Telegram. Safe to call even when disabled."""

    def __init__(self, alert_cfg, logger):
        self.cfg = alert_cfg
        self.log = logger

    @property
    def enabled(self) -> bool:
        return bool(self.cfg.enabled and self.cfg.telegram_token
                    and self.cfg.telegram_chat_id)

    # -- public API ----------------------------------------------------- #
    def send(self, text: str) -> None:
        """Fire-and-forget: never blocks the trading loop, never raises."""
        if not self.enabled:
            return
        threading.Thread(target=self._post, args=(text,), daemon=True).start()

    def send_blocking(self, text: str) -> bool:
        """Send and wait for the result (used by --test-alert)."""
        if not self.cfg.telegram_token or not self.cfg.telegram_chat_id:
            self.log.error("Telegram not configured: set TELEGRAM_BOT_TOKEN and "
                           "TELEGRAM_CHAT_ID in .env (and ALERTS=true).")
            return False
        return self._post(text)

    # -- internals ------------------------------------------------------ #
    def _post(self, text: str) -> bool:
        url = _API.format(token=self.cfg.telegram_token, method="sendMessage")
        data = urllib.parse.urlencode({
            "chat_id": self.cfg.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }).encode()
        try:
            with urllib.request.urlopen(url, data=data, timeout=10) as resp:
                ok = json.loads(resp.read()).get("ok", False)
                if not ok:
                    self.log.warning("Telegram sendMessage returned ok=false.")
                return ok
        except Exception as e:  # network/SSL/timeout — never break trading
            self.log.warning("Telegram alert failed: %s", e)
            return False


def print_chat_ids(token: str) -> None:
    """Helper for --telegram-setup: show chat IDs from recent messages."""
    if not token:
        print("No TELEGRAM_BOT_TOKEN set. Put it in .env first, then re-run.")
        return
    url = _API.format(token=token, method="getUpdates")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            payload = json.loads(resp.read())
    except Exception as e:
        print(f"Could not reach Telegram: {e}")
        return

    if not payload.get("ok"):
        print("Telegram rejected the token. Double-check TELEGRAM_BOT_TOKEN.")
        return

    seen = {}
    for upd in payload.get("result", []):
        msg = upd.get("message") or upd.get("channel_post") or {}
        chat = msg.get("chat", {})
        if "id" in chat:
            name = chat.get("first_name") or chat.get("title") or chat.get("username", "")
            seen[chat["id"]] = name

    if not seen:
        print("No messages found. In Telegram, send your bot any message "
              "(e.g. 'hi') first, then run this again.")
        return

    print("Found these chat IDs — put the right one in .env as TELEGRAM_CHAT_ID:")
    for cid, name in seen.items():
        print(f"   CHAT_ID = {cid}   ({name})")
