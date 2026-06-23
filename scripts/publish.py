#!/usr/bin/env python3
"""
Publish an APPROVED queue item to TikTok.

    python scripts/publish.py <id>

Respects settings.yaml -> publishing.mode:
  inbox  -> sends to TikTok app drafts; finish + post in the app (no audit)
  direct -> Direct Post via API (public requires a passed app audit;
            unaudited apps are forced to SELF_ONLY)
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import metadata, review_queue, tiktok_publish  # noqa: E402
from pipeline.config import settings  # noqa: E402
from pipeline.tiktok_auth import access_token  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    item = review_queue.load(sys.argv[1])

    if item.status != "approved":
        print(f"Refusing: item {item.id} is '{item.status}', not 'approved'. "
              f"Run: python scripts/review.py approve {item.id}")
        sys.exit(1)

    cfg = settings()["publishing"]
    token = access_token()
    video_size = os.path.getsize(item.video_path)
    meta = metadata.build(item.description, item.hashtags)

    # Final compliance lint before anything leaves the machine.
    warns = metadata.lint(meta)
    if warns:
        print("⚠️  Warnings (review before continuing):")
        for w in warns:
            print(f"   - {w}")

    if cfg["mode"] == "inbox":
        print("Uploading to TikTok inbox (you'll finish + post in the app)...")
        res = tiktok_publish.init_inbox_upload(token, video_size=video_size)
        tiktok_publish.upload_file(res["upload_url"], item.video_path)
        status = tiktok_publish.wait_until_done(token, res["publish_id"])
        print(f"Done. Open TikTok → Inbox/Drafts to finish. Status: {status.get('status')}")
        review_queue.set_status(item.id, "published", publish_id=res["publish_id"],
                                notes="sent to inbox; finish in app")

    elif cfg["mode"] == "direct":
        # Step 1: creator info gates the allowed privacy levels.
        info = tiktok_publish.query_creator_info(token)
        allowed = info.get("privacy_level_options", [])
        privacy = cfg["privacy_level"]
        if privacy not in allowed:
            print(f"Privacy '{privacy}' not allowed for this app yet. "
                  f"Allowed: {allowed}. (Unaudited apps only get SELF_ONLY.)")
            privacy = "SELF_ONLY" if "SELF_ONLY" in allowed else allowed[0]
            print(f"Falling back to '{privacy}'.")

        print(f"Direct posting as {privacy}...")
        res = tiktok_publish.init_direct_post(
            token, title=meta.title(), privacy_level=privacy, video_size=video_size,
            disable_comment=cfg["disable_comment"], disable_duet=cfg["disable_duet"],
            disable_stitch=cfg["disable_stitch"],
            is_ai_generated=cfg.get("is_ai_generated", True),
        )
        tiktok_publish.upload_file(res["upload_url"], item.video_path)
        status = tiktok_publish.wait_until_done(token, res["publish_id"])
        print(f"Publish status: {status.get('status')}")
        review_queue.set_status(item.id, "published", publish_id=res["publish_id"])
    else:
        print(f"Unknown publishing.mode: {cfg['mode']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
