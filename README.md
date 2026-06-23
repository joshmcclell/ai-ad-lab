# ai-ad-lab — AI → TikTok publishing workflow

A human-in-the-loop pipeline for producing short-form TikTok videos with
**Higgsfield** (AI video) and **Claude Code**, then publishing them through
**TikTok's Content Posting API** — built to protect your monetization
eligibility, not risk it.

```
 research → brief → generate clips → stitch+caption+music → REVIEW → publish → track
 (Claude)  (you)    (Higgsfield)     (ffmpeg)              (you)    (TikTok)  (Display API)
```

## The honest constraints (read first)

1. **You cannot fully auto-publish *public* videos with an unaudited app.**
   TikTok forces unaudited Content Posting apps to `SELF_ONLY` (private),
   capped at 5 users / 24h. Public Direct Post requires passing TikTok's
   **app audit**. → This repo defaults to **inbox mode**: it pushes finished
   videos to your TikTok app drafts and you tap *Post*. That needs no audit,
   keeps a human in the loop, and is the safest path for a monetized account.
   Switch to `direct` mode in `config/settings.yaml` after your app is audited.

2. **AI-generated content must be disclosed.** TikTok auto-labels AIGC and
   requires creators to flag synthetic media. The pipeline sets the AIGC flag.
   Pure, low-effort AI spam is increasingly **demonetized** — see
   [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md).

3. **No public API gives you $ earnings or watch-time/retention.** Those live
   in TikTok Studio. The API gives views/likes/comments/shares — enough to
   spot winners. See [`docs/TRACKING.md`](docs/TRACKING.md).

4. **Higgsfield clips are short (~5–15s).** We generate several and stitch
   them to hit 15–60s.

## Quick start

```bash
pip install -r requirements.txt          # + install ffmpeg on your system
cp .env.example .env                      # fill TikTok keys
cp config/settings.example.yaml config/settings.yaml   # set your niche

# 1. Authorize your TikTok account (one time)
python scripts/auth_tiktok.py

# 2. Generate a video from a brief into the review queue
python scripts/generate_video.py content/sample/brief.json --generate

# 3. Review it
python scripts/review.py list
python scripts/review.py show <id>
python scripts/review.py approve <id>

# 4. Publish (inbox draft by default)
python scripts/publish.py <id>

# 5. Track what worked
python scripts/tracking_report.py
```

## Docs
- [`docs/WORKFLOW.md`](docs/WORKFLOW.md) — the full 5-step workflow explained
- [`docs/CONTENT_STRATEGY.md`](docs/CONTENT_STRATEGY.md) — trend research with Claude
- [`docs/HIGGSFIELD_SETUP.md`](docs/HIGGSFIELD_SETUP.md) — MCP / CLI / REST
- [`docs/TIKTOK_API_SETUP.md`](docs/TIKTOK_API_SETUP.md) — app, scopes, audit
- [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) — guidelines, copyright, AIGC, monetization
- [`docs/TRACKING.md`](docs/TRACKING.md) — metrics & iteration loop
