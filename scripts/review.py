#!/usr/bin/env python3
"""
Review gate CLI.

    python scripts/review.py list                # show queue
    python scripts/review.py show <id>           # print caption + path
    python scripts/review.py approve <id>        # mark approved (publishable)
    python scripts/review.py reject  <id> "why"  # mark rejected
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import metadata, review_queue  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]

    if cmd == "list":
        for i in review_queue.list_items():
            print(f"{i.id}  [{i.status:9}]  {i.description[:60]}")
    elif cmd == "show":
        i = review_queue.load(sys.argv[2])
        meta = metadata.build(i.description, i.hashtags)
        print(f"id:       {i.id}\nstatus:   {i.status}\nvideo:    {i.video_path}")
        print(f"caption:\n{meta.title()}")
        warns = metadata.lint(meta)
        if warns:
            print("\nwarnings:")
            for w in warns:
                print(f"  - {w}")
    elif cmd == "approve":
        review_queue.set_status(sys.argv[2], "approved")
        print(f"Approved {sys.argv[2]}. Publish: python scripts/publish.py {sys.argv[2]}")
    elif cmd == "reject":
        note = sys.argv[3] if len(sys.argv) > 3 else ""
        review_queue.set_status(sys.argv[2], "rejected", notes=note)
        print(f"Rejected {sys.argv[2]}.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
