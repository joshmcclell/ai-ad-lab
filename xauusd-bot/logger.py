"""Project-wide logging: timestamped output to both console and a rotating file."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent / "logs"
_CONFIGURED = False


def get_logger(name: str = "xauusd-bot") -> logging.Logger:
    """Return a configured logger. Safe to call repeatedly."""
    global _CONFIGURED
    logger = logging.getLogger("xauusd-bot")

    if not _CONFIGURED:
        _LOG_DIR.mkdir(exist_ok=True)
        logger.setLevel(logging.INFO)

        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console = logging.StreamHandler()
        console.setFormatter(fmt)
        logger.addHandler(console)

        # 5 MB per file, keep 5 backups.
        file_handler = RotatingFileHandler(
            _LOG_DIR / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

        logger.propagate = False
        _CONFIGURED = True

    return logger
