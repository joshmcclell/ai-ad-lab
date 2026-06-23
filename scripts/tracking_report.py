#!/usr/bin/env python3
"""
Pull recent video analytics from the TikTok Display API and print a table you
can use to decide what to make more of.

Requires the `video.list` scope (add it to your app + re-auth). The Display
API returns per-video metrics: like_count, comment_count, share_count,
view_count. Watch-time / retention and $ earnings are NOT exposed by the
public API — read those in TikTok Studio / Creator tools (see docs/TRACKING.md).

    python scripts/tracking_report.py
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.tiktok_auth import access_token  # noqa: E402

try:
    from tabulate import tabulate
except ImportError:
    tabulate = None

FIELDS = "id,title,view_count,like_count,comment_count,share_count,create_time"


def main() -> None:
    token = access_token()
    r = requests.post(
        f"https://open.tiktokapis.com/v2/video/list/?fields={FIELDS}",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"max_count": 20},
        timeout=30,
    )
    r.raise_for_status()
    videos = r.json().get("data", {}).get("videos", [])

    rows = []
    for v in videos:
        views = v.get("view_count", 0) or 0
        eng = (v.get("like_count", 0) + v.get("comment_count", 0)
               + v.get("share_count", 0))
        rate = f"{(eng / views * 100):.1f}%" if views else "—"
        rows.append([v.get("title", "")[:30], views, v.get("like_count", 0),
                     v.get("comment_count", 0), v.get("share_count", 0), rate])

    rows.sort(key=lambda x: x[1], reverse=True)
    headers = ["title", "views", "likes", "comments", "shares", "eng. rate"]
    if tabulate:
        print(tabulate(rows, headers=headers))
    else:
        print("\t".join(headers))
        for row in rows:
            print("\t".join(str(c) for c in row))
    print("\nSort by engagement rate to find formats worth repeating.")


if __name__ == "__main__":
    main()
