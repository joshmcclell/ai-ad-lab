# The workflow, step by step

## Step 1 — Content strategy (Claude Code)
Use Claude Code to research trends, hooks, and hashtags **for your specific
niche** (set in `config/settings.yaml`). Claude turns research into a *brief*
JSON the pipeline can act on. Full prompts in
[`CONTENT_STRATEGY.md`](CONTENT_STRATEGY.md).

Output: `content/briefs/<topic>.json` — description, hashtags, scene prompts.

## Step 2 — Video creation (Higgsfield + ffmpeg)
`scripts/generate_video.py`:
1. Generates one short clip per scene with Higgsfield (MCP, CLI, or REST).
2. `pipeline/build_video.py` stitches clips, normalizes to 1080×1920@30fps,
   mixes **licensed** music, and burns in captions from an `.srt`.
3. Adds the draft to the review queue (`content/queue/<id>.json`).

Captions, text overlays, and effects: captions are burned via ffmpeg
`subtitles`; for fancier word-by-word styling do it in Higgsfield or a
captioning tool, then export an `.srt`. See [`HIGGSFIELD_SETUP.md`](HIGGSFIELD_SETUP.md).

## Step 3 — Review gate (you)
`scripts/review.py` lists drafts, shows the rendered caption + compliance
lint warnings, and lets you `approve` or `reject`. **Nothing publishes
without an explicit `approve`.** This is what keeps low-quality AI output off
a monetized account.

## Step 4 — Upload (TikTok Content Posting API)
`scripts/publish.py`:
- **inbox mode (default):** uploads to your TikTok app drafts; you do the
  final tap. No app audit required. Recommended.
- **direct mode:** queries creator info → inits a Direct Post → uploads bytes
  → polls status. Public visibility requires a passed audit; until then it's
  forced to `SELF_ONLY`.

Metadata (title/description/hashtags, AIGC flag, comment/duet/stitch toggles)
is built by `pipeline/metadata.py` and validated before upload.

## Step 5 — Tracking & improvement
`scripts/tracking_report.py` pulls per-video views/likes/comments/shares via
the Display API and ranks by engagement rate. Pair it with TikTok Studio for
watch-time and earnings. Feed the winners back into Step 1. See
[`TRACKING.md`](TRACKING.md).

## Where automation can and can't go
- **Fully automatable:** research → generate → stitch → enqueue → (inbox) upload.
- **Requires a human or an audit:** public auto-posting. By design we keep the
  review gate even after audit — it's cheap insurance for monetization.
- **Scheduling:** wrap `generate_video.py`/`publish.py` in cron or a GitHub
  Action once you're comfortable. Keep the approve step manual until you trust
  the output.
