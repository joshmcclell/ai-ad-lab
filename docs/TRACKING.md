# Tracking & improvement

## What you can pull via API (`scripts/tracking_report.py`)
Using the Display API `video.list` scope, per video:
- `view_count`, `like_count`, `comment_count`, `share_count`, `create_time`
- The script computes an **engagement rate** = (likes+comments+shares)/views
  and ranks your last ~20 videos.

```bash
python scripts/tracking_report.py
```

## What you must read in-app (no public API)
- **Watch time / average view duration / completion rate** — the metrics the
  algorithm cares about most.
- **Retention graph** (where viewers drop off — fix your hooks here).
- **Traffic source** (FYP vs profile vs search).
- **Earnings / RPM** — TikTok Studio → Creator tools / monetization dashboard.

Open **TikTok app → Profile → Menu → Creator tools → Analytics**, or
**TikTok Studio** on desktop.

## A simple weekly loop
1. Run `tracking_report.py`; note the top 3 by engagement rate.
2. In TikTok Studio, check **average watch time** for those same 3.
3. Identify the common factor (topic? format? hook style? length?).
4. Write next week's briefs around that factor (Step 1 prompts in
   `CONTENT_STRATEGY.md`).
5. Kill formats with low watch time even if views looked okay — watch time
   drives both reach and money.

## Optional: log your own history
Export the report to CSV over time so you can see trends:
```bash
python scripts/tracking_report.py > data/$(date +%F)_report.txt
```
(`data/` is gitignored.) For richer analysis, append the rows to a CSV and
chart engagement vs. length / posting time.
