"""
trade_logger.py
===============
Append-only CSV logging of every trade the bot opens and closes, plus a small
console logger. Each row captures time, price, direction, lot, SL, TP and
result so the strategy can be audited and analysed offline.
"""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

# --------------------------------------------------------------------------- #
# Console logger                                                               #
# --------------------------------------------------------------------------- #
def get_logger(name: str = "scalper", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                datefmt="%Y-%m-%d %H:%M:%S")
        # Console output.
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        # Persistent file output: every event (incl. each trade taken) is
        # appended to logs/bot.log so nothing is lost when the terminal closes.
        try:
            os.makedirs("logs", exist_ok=True)
            fh = logging.FileHandler(os.path.join("logs", "bot.log"))
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except Exception:
            pass  # never let logging break trading
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


# --------------------------------------------------------------------------- #
# Trade record + CSV writer                                                    #
# --------------------------------------------------------------------------- #
CSV_FIELDS = [
    "open_time", "close_time", "symbol", "direction", "lot",
    "entry_price", "stop_loss", "take_profit", "exit_price",
    "atr", "money_at_risk", "result", "pnl", "balance_after",
    "order_ticket", "comment",
]


@dataclass
class TradeRecord:
    open_time: str
    symbol: str
    direction: str
    lot: float
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float = 0.0
    money_at_risk: float = 0.0
    order_ticket: Optional[int] = None
    comment: str = ""
    # Filled in on close:
    close_time: str = ""
    exit_price: float = 0.0
    result: str = ""        # "TP" | "SL" | "MANUAL" | "WIN" | "LOSS"
    pnl: float = 0.0
    balance_after: float = 0.0


class TradeLogger:
    """Writes TradeRecords to a CSV file, creating the header on first use."""

    def __init__(self, path: str):
        self.path = path
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()

    def write(self, record: TradeRecord) -> None:
        row = {k: getattr(record, k) for k in CSV_FIELDS}
        with open(self.path, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=CSV_FIELDS).writerow(row)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
