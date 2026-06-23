# Roadmap: launch → scale

A staged plan. Don't skip the foundation phases to chase ads — most failed
dropshipping stores fail on product choice and store trust, not creative.

## Phase 0 — Foundations (week 1)
- Register the business; understand VAT/IOSS (see `compliance-uk-eu.md`).
- Pick a niche/positioning with Claude (Workflow 1). Validate demand with **live**
  data (Trends, ad libraries, competitor stores) — not just Claude's opinion.
- Create the Shopify store skeleton, Anthropic API key, Higgsfield account.

## Phase 1 — Store setup & config (week 1–2)
- **Theme:** start with a fast, clean free theme (e.g. Dawn). Don't over-customise yet.
- **Pages/policies:** all six legal pages live (compliance checklist).
- **Navigation:** simple — Home, Shop/Collections, About, Contact, Policies in footer.
- **Payments:** Shopify Payments (+ PayPal). Confirm payouts work.
- **Shipping:** zones + **honest** delivery times; decide free vs flat-rate.
- **Apps:** cookie consent, reviews (genuine only), email.
- **Pixels/tags:** install Meta Pixel + Google tag (gated behind cookie consent).

## Phase 2 — First products (week 2)
- Source 1–5 hero products from a reliable supplier (CJ Dropshipping, Zendrop, or
  a vetted AliExpress seller). Order samples for your hero product.
- `npm run product` for copy → review → add price/images → publish.
- Generate clean PDP imagery in Higgsfield.

## Phase 3 — Creative & first ads (week 3)
- `npm run adcopy` → 3 angles → Higgsfield creative in 1:1, 4:5, 9:16.
- Launch small: one campaign, 2–3 ad sets (one per angle), modest equal budgets.
- Let the platform optimise; judge on CTR, CPC, add-to-cart, ROAS — not vanity metrics.

## Phase 4 — Iterate on data (week 3–6)
- Kill losing creative; pour budget into winners. Ask Claude to generate fresh
  variants of the winning angle (and new Higgsfield visuals).
- Add the order-follow-up automation (`webhookServer.ts`) and abandoned-cart email.
- Start the blog/SEO engine (Workflow 5) for free traffic compounding over time.

## Phase 5 — Systematise & scale (month 2+)
- Cache the brand/compliance system prompt; move bulk copy jobs to Claude's Batch API.
- Automate recurring work with n8n / scheduled jobs (content, reporting).
- Expand winning products into a small range; introduce upsells/bundles.
- Consider automating campaign creation via the Meta Marketing / Google Ads APIs
  **only once you have a repeatable, profitable manual process.**

## What to measure
| Metric | Why |
|--------|-----|
| Contribution margin per order | Are you actually profitable after COGS + shipping + ad spend + fees? |
| ROAS / CPA | Ad efficiency per product/angle |
| CTR & CPC | Creative quality signal (fix creative before scaling) |
| Conversion rate | Store/PDP trust & offer strength |
| Refund/chargeback rate | Compliance & delivery-expectation health |

## Common mistakes to avoid
- Treating Higgsfield as an ad-buyer (it isn't — it makes creative).
- Publishing AI copy unreviewed → compliance and accuracy risk.
- Hiding long shipping times → chargebacks and ASA trouble.
- Scaling spend before the product/creative is validated.
- Ignoring VAT/IOSS until it's a problem.
- Restricted products (health claims, branded goods) → account bans.
