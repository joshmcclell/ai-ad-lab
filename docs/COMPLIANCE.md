# Compliance & safety — protect your monetization

Demonetization usually comes from a few avoidable mistakes. This is the
checklist the pipeline is built around.

## 1. AI-generated content disclosure (mandatory)
- TikTok requires creators to **disclose AI-generated/synthetic media**, and
  auto-applies an "AI-generated" label (often via C2PA metadata from tools).
- The pipeline sets `is_aigc: true` on Direct Post and the lint warns if your
  caption doesn't mention AI. Keep `publishing.is_ai_generated: true` while
  your videos are AI-made. **Do not** try to strip AI labels — that risks
  removal and demonetization.
- Realistic AI depictions of real people/events need extra care; avoid
  anything that could mislead (esp. public figures, news, elections).

## 2. Originality (this is where AI accounts get demonetized)
TikTok's Creator Rewards / Creativity programs **exclude "unoriginal,"
low-effort, or duplicated content**, including raw AI output with no creative
input. To stay eligible:
- Add a clear **human creative layer**: your script/voice/POV, editing,
  commentary, a consistent format.
- Don't post the same clip repeatedly or near-duplicates.
- Don't compile other people's videos/slideshows without transformation.

## 3. Copyright & licensing
- **Music:** use the **TikTok Commercial Music Library** (in-app) for
  monetized/business posts, or audio you've actually licensed (e.g. Epidemic
  Sound, Artlist, royalty-free). Popular chart music is usually **not**
  cleared for monetized/commercial use and can mute your video or block reach.
- **Footage/images:** only use AI-generated assets you created, or properly
  licensed stock. Don't feed copyrighted clips/characters into Higgsfield.
- **Fonts/overlays:** use license-clear fonts.
- Keep proof of license for anything not self-generated.

## 4. Community Guidelines basics
Avoid: violent/graphic content, hate, harassment, dangerous acts, regulated
goods, sexual content, misinformation, and **unverified financial/health
claims** ("guaranteed returns", "miracle cure"). The lint in
`pipeline/metadata.py` flags a starter list of risky phrases — extend it.

## 5. Monetization-specific rules
- Meet the program's **eligibility** (followers, age, region, clean account)
  and keep it clean — strikes/violations can demonetize.
- **Creator Rewards Program** rewards **original videos > 1 minute** with
  strong watch-time. If that's your target, set `video.target_seconds: 61`.
- No artificial engagement (bought views/follows), no gating ("follow to see
  part 2" spam can be down-ranked).
- Branded content must use the **branded-content toggle** + disclosure.

## 6. Pre-publish checklist (the review gate enforces the spirit of this)
- [ ] AI disclosure on (flag + caption note)
- [ ] Music is from Commercial Music Library or licensed
- [ ] No copyrighted footage/characters/logos
- [ ] Clear original creative layer (not raw AI dump)
- [ ] No prohibited topics / unverified claims
- [ ] Caption: hook + value + 3–6 focused hashtags
- [ ] Length matches your monetization target
