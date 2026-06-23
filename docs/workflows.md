# Sample workflows & automation logic

Each workflow lists the trigger, the steps, and where the code/tool lives.

---

## Workflow 1 — Product research & validation (Claude)

**Goal:** find profitable, low-competition products before committing.

1. Ask Claude to brainstorm + pressure-test niches against criteria: solves a
   real problem, £15–£70 price band, lightweight/cheap to ship, not heavily
   saturated, not restricted (no supplements, vapes, medical claims, branded
   goods).
2. Have Claude turn winners into a scoring table (demand, margin, competition,
   ad-friendliness, shipping risk).
3. **Validate with real data** — Claude's training has a cutoff, so confirm with
   live signals: Google Trends, AliExpress/CJ order counts, TikTok/Meta ad
   libraries, competitor stores. (Use Claude's web search tool or do it manually.)

> Claude is excellent at *structuring and critiquing* product ideas; it is not a
> live market-data source. Always validate demand with current data.

---

## Workflow 2 — Idea → live product page

**Trigger:** you pick a winning product.

1. `npm run product -- "<idea>"` → Claude writes title, HTML description, SEO,
   tags → creates a **DRAFT** product in Shopify.
2. Human reviews copy for accuracy/compliance, adds price, supplier, images.
3. Generate hero/gallery imagery in **Higgsfield** (Marketing Studio or
   `generate_image`); upscale with `upscale_image`; remove backgrounds for clean
   PDP shots with `remove_background`.
4. Publish.

---

## Workflow 3 — Ad creative production

**Trigger:** product is live, you're ready to advertise.

1. `npm run adcopy -- "<idea>"` → Claude returns 3 distinct angles, each with a
   headline, primary text, and a **visual brief**.
2. Paste each `visualBrief` into **Higgsfield** to generate image and/or video
   creative (use `reframe` to produce 1:1, 4:5, and 9:16 versions for different
   placements).
3. Optionally score variants with Higgsfield's `virality_predictor` before spend.
4. Upload creative + copy to **Meta/Google/TikTok**, one ad set per angle, small
   equal budgets, let the platform find winners.

---

## Workflow 4 — Order follow-up & retention (automated)

**Trigger:** Shopify `orders/create` webhook.

1. `src/webhookServer.ts` verifies the HMAC, then calls Claude to draft a
   personalised confirmation/thank-you email.
2. Send via your email tool (Shopify Email, Klaviyo, or the Gmail integration).
3. Schedule a post-delivery review request and a win-back sequence (Claude writes
   the whole flow; your ESP sends it).

---

## Workflow 5 — Blog & SEO content engine

**Trigger:** weekly schedule (cron / n8n).

1. Claude generates a content calendar around buyer intent keywords.
2. For each topic, Claude drafts an article (with internal links to products),
   meta title/description, and a social caption.
3. Push as a Shopify blog article (Admin GraphQL `articleCreate`) in **draft**
   for review.

---

## Automation logic: when to use what

- **Webhook + script (this repo):** anything event-driven and custom (order
  emails, auto-tagging, inventory sync).
- **Scheduled job (cron / GitHub Actions / n8n):** recurring batch work (weekly
  blogs, nightly description refresh via Claude's Batch API).
- **No-code (Make / n8n / Zapier):** simple A→B handoffs you don't want to host.
- **Human-in-the-loop everywhere copy goes public.** Generate to **draft**, review,
  then publish. This is both a quality and a compliance safeguard.

## Guardrails to bake in

- Idempotency: webhooks can fire more than once — de-dupe on order/event ID.
- Rate limits: Shopify GraphQL uses a cost-based limit; back off on `THROTTLED`.
- Cost control: cache the brand/compliance system prompt; use Sonnet/Haiku or the
  Batch API for bulk; cap `max_tokens`.
- Never expose API keys client-side; keep them in `.env` / your host's secrets.
