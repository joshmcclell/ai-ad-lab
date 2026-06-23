# Content strategy with Claude Code

Set `account.niche` in `config/settings.yaml` first — everything keys off it.

## Researching trends (prompts you can paste into Claude Code)

**Trend + format scan**
> "My TikTok niche is `<niche>`. Using web search, find 5 topics trending in
> this niche in the last 2 weeks, the video *format* that's working for each
> (talking-head, screen-record, list, story, B-roll+VO), a strong 3-second
> hook line for each, and 4–6 hashtags mixing one broad + two niche + one
> trend tag. Avoid anything that risks TikTok monetization. Output as a table."

**Turn a winner into a brief**
> "Take row 2 and write a `brief.json` matching `content/sample/brief.json`:
> a punchy description (with a hook in the first line), 4–6 hashtags, and 3–4
> Higgsfield scene prompts (9:16, cinematic, 8s each) that tell the story.
> Add an AI disclosure to the description."

**Caption / SRT**
> "Write a 34-second voiceover script for this brief and an `.srt` with
> timings so captions can be burned in. Keep sentences short for readability."

## What tends to work for monetized short-form
- **Hook in the first 1–2 seconds** (a question, a bold claim, motion).
- **Tight format you repeat** so the algorithm and audience learn your brand.
- **Watch-time first.** Pacing, captions, and a payoff at the end beat
  hashtag tricks. (Captions alone lift completion meaningfully.)
- **Post consistently** (daily-ish) at times your audience is active
  (`account.timezone`). Check your own analytics rather than generic charts.
- **Series / "part 2"** for genuine multi-part stories — not as a cheap gate.
- For **Creator Rewards**, aim for **>1 minute** with real retention.

## Hashtag approach
3–6 focused tags > 15 generic ones. One broad reach tag + two niche tags +
one current trend tag. `pipeline/metadata.py` caps at 6 and de-dupes.

## The loop
Research → brief → produce → review → publish → read `tracking_report.py` +
TikTok Studio → double down on the format/topic with the best **engagement
rate and watch-time**, cut the rest. See [`TRACKING.md`](TRACKING.md).
