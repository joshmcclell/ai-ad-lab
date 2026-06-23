#!/usr/bin/env python3
"""
Generate a video from a content brief and add it to the review queue (status
'draft'). It does NOT publish — review.py + publish.py handle that.

Usage:
    python scripts/generate_video.py briefs/my_brief.json

Brief JSON shape:
{
  "description": "3 underrated VS Code shortcuts that save hours",
  "hashtags": ["#vscode", "#coding", "#productivity"],
  "scenes": [
    "close-up of hands typing fast on a mechanical keyboard, neon desk",
    "screen recording style shot of code refactoring itself, smooth zoom"
  ],
  "music": "content/music/licensed_track.mp3",   // optional, must be licensed
  "captions_srt": "content/captions/my_brief.srt" // optional
}

If you use the Higgsfield MCP server in Claude Code, you can instead ask Claude
to generate the scene clips into content/clips/<id>/ and skip --generate.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import build_video, metadata, review_queue  # noqa: E402
from pipeline.config import ROOT, settings  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("brief", help="Path to brief JSON")
    ap.add_argument("--generate", action="store_true",
                    help="Generate clips via Higgsfield REST (else expects clips present)")
    args = ap.parse_args()

    brief = json.loads(Path(args.brief).read_text())
    item = review_queue.QueueItem(
        video_path="",  # filled after render
        description=brief["description"],
        hashtags=metadata.normalize_hashtags(brief.get("hashtags", [])),
    ).save()

    clips_dir = ROOT / "content" / "clips" / item.id
    clips_dir.mkdir(parents=True, exist_ok=True)

    if args.generate:
        from pipeline.higgsfield_client import generate_clip
        clips = []
        for i, scene in enumerate(brief["scenes"]):
            print(f"Generating clip {i + 1}/{len(brief['scenes'])}: {scene[:60]}...")
            clips.append(generate_clip(scene, clips_dir / f"clip_{i:02d}.mp4"))
    else:
        clips = sorted(clips_dir.glob("*.mp4"))
        if not clips:
            print(f"No clips in {clips_dir}. Generate them (MCP/CLI) or pass --generate.")
            sys.exit(1)

    renders = ROOT / "content" / "renders"
    stitched = build_video.concat_clips(clips, renders / f"{item.id}_raw.mp4")
    final = build_video.finalize(
        stitched, renders / f"{item.id}.mp4",
        music=brief.get("music"),
        srt_captions=brief.get("captions_srt"),
    )

    meta = metadata.build(item.description, item.hashtags)
    warnings = metadata.lint(meta)

    item.video_path = str(final)
    item.save()

    print(f"\n✅ Draft queued: {item.id}")
    print(f"   Video: {final}")
    print(f"   Caption preview:\n   {meta.title()[:200]}")
    dur = settings()["video"]
    print(f"   Target spec: {dur['resolution']} @ {dur['fps']}fps, "
          f"{dur['min_seconds']}-{dur['max_seconds']}s")
    if warnings:
        print("\n⚠️  Compliance warnings:")
        for w in warnings:
            print(f"   - {w}")
    print(f"\nNext: review it ->  python scripts/review.py approve {item.id}")


if __name__ == "__main__":
    main()
