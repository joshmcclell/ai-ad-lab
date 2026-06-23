#!/usr/bin/env python3
"""One-time TikTok authorization. Run: python scripts/auth_tiktok.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.tiktok_auth import authorize  # noqa: E402

if __name__ == "__main__":
    authorize()
