"""Optional Telegram alerts on trade open/close. Silently no-ops if disabled.

Enable by setting TELEGRAM_ENABLED=true plus TELEGRAM_BOT_TOKEN and
TELEGRAM_CHAT_ID in .env. Failures never crash the bot — they are logged and
swallowed, because a missed alert must not stop trading logic.
"""
from __future__ import annotations

from config import CONFIG
from logger import get_logger

log = get_logger()


def send(message: str) -> None:
    if not CONFIG.telegram_enabled:
        return
    if not (CONFIG.telegram_bot_token and CONFIG.telegram_chat_id):
        log.warning("Telegram enabled but token/chat_id missing — skipping alert.")
        return
    try:
        import requests  # imported lazily so it's only required when alerts are on

        url = f"https://api.telegram.org/bot{CONFIG.telegram_bot_token}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": CONFIG.telegram_chat_id, "text": message},
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("Telegram alert failed (%s): %s", resp.status_code, resp.text)
    except Exception as exc:  # noqa: BLE001 — alerts must never break trading
        log.warning("Telegram alert error: %s", exc)
