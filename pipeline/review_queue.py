"""
Simple file-based review gate. A video must be explicitly approved before
publish.py will send it to TikTok. This is the human-in-the-loop safety net
that protects monetization eligibility.

Each item is a JSON file in content/queue/. Status flows:
    draft -> approved -> published   (or  draft -> rejected)
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import ROOT

QUEUE_DIR = ROOT / "content" / "queue"


@dataclass
class QueueItem:
    video_path: str
    description: str
    hashtags: list[str] = field(default_factory=list)
    status: str = "draft"           # draft | approved | rejected | published
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    created_at: int = field(default_factory=lambda: int(time.time()))
    publish_id: str | None = None
    notes: str = ""

    def path(self) -> Path:
        return QUEUE_DIR / f"{self.id}.json"

    def save(self) -> "QueueItem":
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        self.path().write_text(json.dumps(asdict(self), indent=2))
        return self


def load(item_id: str) -> QueueItem:
    data = json.loads((QUEUE_DIR / f"{item_id}.json").read_text())
    return QueueItem(**data)


def list_items(status: str | None = None) -> list[QueueItem]:
    if not QUEUE_DIR.exists():
        return []
    items = [QueueItem(**json.loads(p.read_text())) for p in QUEUE_DIR.glob("*.json")]
    if status:
        items = [i for i in items if i.status == status]
    return sorted(items, key=lambda i: i.created_at)


def set_status(item_id: str, status: str, **updates) -> QueueItem:
    item = load(item_id)
    item.status = status
    for k, v in updates.items():
        setattr(item, k, v)
    return item.save()
