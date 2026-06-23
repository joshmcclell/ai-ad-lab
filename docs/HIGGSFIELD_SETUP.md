# Higgsfield setup

Pick **one** integration mode and set it in `config/settings.yaml`
(`higgsfield.mode`).

## Option A — MCP server inside Claude Code (recommended)
Best fit when you're driving this from Claude Code. Hosted server, OAuth, no
API key, no proxy.

```bash
claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp
claude mcp list           # verify it connected
```
First use opens a browser to sign in to your Higgsfield account. Then, in a
Claude Code session, just ask:

> "Generate a 9:16 8-second clip with the Soul model: *close-up of hands
> typing on a neon mechanical keyboard*, then a second clip: *code refactoring
> itself, smooth zoom*. Save both to `content/clips/<id>/`."

Claude calls Higgsfield's tools and writes the mp4s. Then run
`generate_video.py` **without** `--generate` to stitch + caption them.

## Option B — REST API (for scheduled / non-interactive runs)
1. In your Higgsfield dashboard (Studio plan for API access), create an API
   key + secret.
2. Put `HF_API_KEY`, `HF_SECRET`, `HIGGSFIELD_BASE_URL` in `.env`.
3. Confirm the exact endpoint paths/field names in your dashboard docs and
   adjust them in `pipeline/higgsfield_client.py` (they're isolated in
   `generate_clip()`). The shape is stable: submit job → poll → download mp4.
4. Run `python scripts/generate_video.py <brief> --generate`.

## Option C — CLI
Higgsfield also ships a CLI (`higgsfield.ai/cli`) usable from Claude Code for
scriptable generation. Use it to produce clips into `content/clips/<id>/`,
then stitch as in Option A.

## Models & length
- Models include **Soul, Cinema Studio, Veo, Kling, Minimax Hailuo**, etc.
  Set `higgsfield.default_model`. Cinematic/photoreal → Cinema Studio/Veo;
  fast stylized → Soul/Kling.
- Native clips are **~5–15s**. Set `higgsfield.clip_seconds` and provide
  enough scenes in the brief to reach `video.target_seconds` after stitching.

## Captions, overlays, music
- **Captions:** supply an `.srt` in the brief (`captions_srt`); ffmpeg burns
  it in with a readable style (`pipeline/build_video.py`). Auto-generate the
  `.srt` from your script, or have Claude write timings.
- **Text overlays / effects:** add them in Higgsfield prompts, or extend
  `build_video.py` with ffmpeg `drawtext`/overlay filters.
- **Music:** must be licensed (see `COMPLIANCE.md`). Point `music` in the brief
  at a licensed file. For published-in-app (inbox mode) you can instead add a
  track from TikTok's Commercial Music Library in the app.
