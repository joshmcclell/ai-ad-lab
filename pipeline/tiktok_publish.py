"""
TikTok Content Posting API client.

Two modes:
  * inbox  -> upload to the user's TikTok app drafts; the user opens the app,
              adds final touches, and taps Post. Works for UNAUDITED apps.
  * direct -> Direct Post fully via API. UNAUDITED apps are forced to
              SELF_ONLY (private). Public posting requires passing TikTok's
              audit for the video.publish scope.

Flow for direct post (per TikTok docs):
  1. POST /v2/post/publish/creator_info/query/   -> allowed privacy levels, caps
  2. POST /v2/post/publish/video/init/           -> publish_id + upload_url
  3. PUT bytes to upload_url                      -> uploads the file
  4. POST /v2/post/publish/status/fetch/          -> poll until PUBLISH_COMPLETE

Rate limit: 6 requests/min per user access token.
Docs: https://developers.tiktok.com/doc/content-posting-api-get-started
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

API = "https://open.tiktokapis.com"
# TikTok wants a single chunk for files under 64MB. Min chunk is 5MB.
WHOLE_FILE_CHUNK_LIMIT = 64 * 1024 * 1024


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def query_creator_info(token: str) -> dict:
    """Step 1. Must be called before a direct post to learn allowed options."""
    r = requests.post(
        f"{API}/v2/post/publish/creator_info/query/",
        headers=_headers(token),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"creator_info error: {data['error']}")
    return data["data"]


def _init(token: str, endpoint: str, payload: dict) -> dict:
    r = requests.post(f"{API}{endpoint}", headers=_headers(token), json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    err = data.get("error", {})
    if err.get("code") not in (None, "ok"):
        raise RuntimeError(f"init error ({endpoint}): {err}")
    return data["data"]


def init_direct_post(token: str, *, title: str, privacy_level: str, video_size: int,
                     disable_comment: bool = False, disable_duet: bool = False,
                     disable_stitch: bool = False, is_ai_generated: bool = True) -> dict:
    """Step 2 (direct). Returns {publish_id, upload_url}."""
    payload = {
        "post_info": {
            "title": title,                       # hashtags/@mentions go in here
            "privacy_level": privacy_level,
            "disable_comment": disable_comment,
            "disable_duet": disable_duet,
            "disable_stitch": disable_stitch,
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        },
    }
    # AI-generated disclosure (TikTok policy for synthetic media).
    if is_ai_generated:
        payload["post_info"]["is_aigc"] = True
    return _init(token, "/v2/post/publish/video/init/", payload)


def init_inbox_upload(token: str, *, video_size: int) -> dict:
    """Step 2 (inbox). Lands in the app as a draft. Returns {publish_id, upload_url}."""
    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1,
        }
    }
    return _init(token, "/v2/post/publish/inbox/video/init/", payload)


def upload_file(upload_url: str, path: str | Path) -> None:
    """Step 3. PUT the whole file in a single chunk (files < 64MB)."""
    size = os.path.getsize(path)
    if size > WHOLE_FILE_CHUNK_LIMIT:
        raise ValueError(
            f"{path} is {size} bytes (>64MB). Implement multi-chunk upload "
            "(5MB-64MB chunks) for files this large."
        )
    with open(path, "rb") as fh:
        data = fh.read()
    r = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
        data=data,
        timeout=300,
    )
    r.raise_for_status()


def fetch_status(token: str, publish_id: str) -> dict:
    r = requests.post(
        f"{API}/v2/post/publish/status/fetch/",
        headers=_headers(token),
        json={"publish_id": publish_id},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"]


def wait_until_done(token: str, publish_id: str, timeout_s: int = 300) -> dict:
    """Poll status until a terminal state or timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = fetch_status(token, publish_id)
        state = status.get("status")
        if state in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX", "FAILED"):
            return status
        time.sleep(5)
    return fetch_status(token, publish_id)
