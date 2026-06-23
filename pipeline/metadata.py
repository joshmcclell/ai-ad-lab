"""Build and validate TikTok post metadata (title, description, hashtags)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import settings

# Words/phrases that commonly trigger demonetization or limited reach.
# Not exhaustive — TikTok does not publish a full list. Keep editing this.
RISKY_TERMS = {
    "guarantee", "miracle cure", "get rich quick", "free money",
    "click the link in bio to buy", "kill", "blood", "gun",
}


@dataclass
class PostMetadata:
    description: str
    hashtags: list[str] = field(default_factory=list)

    def title(self) -> str:
        """TikTok's `title` field holds caption + hashtags + @mentions."""
        cfg = settings()
        footer = cfg["metadata"].get("description_footer", "")
        tags = " ".join(self.hashtags)
        parts = [self.description.strip()]
        if footer:
            parts.append(footer.strip())
        if tags:
            parts.append(tags.strip())
        text = "\n\n".join(p for p in parts if p)
        return text[: cfg["metadata"]["max_title_chars"]]


def normalize_hashtags(tags: list[str]) -> list[str]:
    out = []
    for t in tags:
        t = t.strip()
        if not t:
            continue
        if not t.startswith("#"):
            t = "#" + t
        t = re.sub(r"[^#\w]", "", t)
        if t != "#":
            out.append(t)
    # de-dup, keep order
    seen, deduped = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower())
            deduped.append(t)
    return deduped


def build(description: str, hashtags: list[str] | None = None) -> PostMetadata:
    cfg = settings()
    tags = normalize_hashtags((hashtags or []) + cfg["metadata"]["default_hashtags"])
    # 3-6 hashtags is the sweet spot.
    return PostMetadata(description=description, hashtags=tags[:6])


def lint(meta: PostMetadata) -> list[str]:
    """Return a list of warnings. Empty list = looks good."""
    warnings: list[str] = []
    text = meta.title().lower()
    for term in RISKY_TERMS:
        if term in text:
            warnings.append(f"Contains risky phrase: '{term}'")
    if len(meta.hashtags) == 0:
        warnings.append("No hashtags — add 3-6 focused tags.")
    if len(meta.hashtags) > 8:
        warnings.append("Too many hashtags (>8) can look spammy.")
    if "ai" not in text and settings()["publishing"].get("is_ai_generated"):
        warnings.append(
            "Content is AI-generated but caption doesn't disclose it. "
            "TikTok requires AIGC disclosure; the API flag is set, but a "
            "visible note is good practice."
        )
    return warnings
