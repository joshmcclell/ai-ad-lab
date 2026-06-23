"""
Higgsfield video generation adapter.

There are three ways to drive Higgsfield. Pick one in settings.yaml
(higgsfield.mode):

  1. "mcp"  (recommended in Claude Code)
     Install the hosted MCP server once:
         claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp
     Then Claude Code calls Higgsfield tools directly (OAuth in browser, no key).
     In that setup you do NOT call this module — you ask Claude to generate
     clips and save them under content/clips/. This module is the fallback for
     non-interactive / scheduled runs.

  2. "rest"
     Call the Higgsfield REST API with HF_API_KEY / HF_SECRET. Endpoint paths
     differ by account; confirm them in your Higgsfield dashboard and set them
     below. The shape (submit job -> poll -> download) is stable.

  3. SDK
     `pip install` the official client (github.com/higgsfield-ai/higgsfield-client)
     and swap generate_clip() to call it.

NOTE: Higgsfield clips are short (~5-15s). To hit a 15-60s TikTok we generate
several clips and stitch them in build_video.py.
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

from .config import env, settings


def _hf_headers() -> dict:
    key = env("HF_API_KEY", required=True)
    secret = env("HF_SECRET")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if secret:
        headers["hf-secret"] = secret
    return headers


def generate_clip(prompt: str, out_path: str | Path, *, model: str | None = None,
                  seconds: int | None = None, image_path: str | None = None) -> Path:
    """
    Submit a generation job, poll until ready, download the mp4.

    Confirm the exact endpoint paths/field names against your Higgsfield
    dashboard docs — they are isolated here so you only edit this function.
    """
    cfg = settings()["higgsfield"]
    base = env("HIGGSFIELD_BASE_URL", "https://platform.higgsfield.ai")
    model = model or cfg["default_model"]
    seconds = seconds or cfg["clip_seconds"]
    out_path = Path(out_path)

    body = {"model": model, "prompt": prompt, "duration": seconds,
            "aspect_ratio": settings()["video"]["aspect_ratio"]}
    if image_path:
        body["input_image_url"] = image_path  # image-to-video

    submit = requests.post(f"{base}/v1/video/generate", headers=_hf_headers(),
                           json=body, timeout=60)
    submit.raise_for_status()
    job_id = submit.json()["id"]

    # Poll (~45s average per the docs).
    for _ in range(60):
        time.sleep(5)
        st = requests.get(f"{base}/v1/video/{job_id}", headers=_hf_headers(), timeout=30)
        st.raise_for_status()
        data = st.json()
        if data.get("status") == "completed":
            url = data["output"]["video_url"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with requests.get(url, stream=True, timeout=300) as media:
                media.raise_for_status()
                with open(out_path, "wb") as fh:
                    for chunk in media.iter_content(chunk_size=1 << 16):
                        fh.write(chunk)
            return out_path
        if data.get("status") == "failed":
            raise RuntimeError(f"Higgsfield job {job_id} failed: {data}")
    raise TimeoutError(f"Higgsfield job {job_id} did not finish in time")
