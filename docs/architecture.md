# Architecture: how Shopify, Claude & Higgsfield fit together

## Roles (no overlap, no gaps)

| Layer | Tool | Owns |
|-------|------|------|
| **Storefront & commerce** | Shopify | Catalog, checkout, payments, orders, customers, taxes, shipping. The single source of truth. |
| **Intelligence & content** | Claude | Research, product copy, blogs, email, ad copy, automation logic, data summarisation. |
| **Creative production** | Higgsfield | Ad images, product videos, UGC-style clips, the "Marketing Studio" product-ad workflow. |
| **Ad delivery** *(not in your 3 tools)* | Meta / Google / TikTok Ads | Targeting, budgets, bidding, where ads actually serve. |

> The single most common misconception: that Higgsfield "runs ads". It
> generates the *creative*. You still upload that creative to an ad platform
> and manage spend there.

## Data flow

```
1. Claude  → product research + copy ───────────────┐
2. Shopify ← product created (draft) ◀──────────────┘
3. Claude  → ad copy + a "visual brief" ────────────┐
4. Higgsfield ← visual brief → generates image/video┘
5. Ad platform ← creative + copy uploaded → ads run
6. Shopify ← traffic & orders; pixel/tag fires conversions back to ad platform
7. Shopify → webhook (orders/create) → your server → Claude drafts follow-up email
```

## APIs, webhooks & connectors you'll actually use

### Shopify
- **Admin GraphQL API** — create/update products, read orders, manage inventory.
  Endpoint: `https://{store}.myshopify.com/admin/api/{version}/graphql.json`,
  header `X-Shopify-Access-Token`. (See `src/shopifyClient.ts`.)
- **Webhooks** — Shopify pushes events to your URL. Key topics:
  `orders/create`, `orders/fulfilled`, `products/create`, `customers/create`,
  `checkouts/abandoned` (via the app/flow). Always HMAC-verify (see
  `src/webhookServer.ts`).
- **Storefront API** — only if you build a custom/headless front end. Not needed
  for a standard Shopify theme.
- **Custom app** — the modern way to get API credentials (Settings → Apps →
  Develop apps). No public-app review needed for your own store.

### Claude (Anthropic API)
- **Messages API** (`/v1/messages`) via the official SDK. Model `claude-opus-4-8`.
- **Structured outputs** (`output_config.format`) — forces valid JSON for
  product fields, ad variants, etc. (used in `src/generateProductContent.ts`).
- **Prompt caching** — cache your brand/voice/compliance system prompt to cut
  cost ~90% on the cached portion when you generate copy in bulk.
- **Batch API** — 50% cheaper for non-urgent bulk jobs (e.g. rewriting 500
  product descriptions overnight).

### Higgsfield
- Primarily used through its **app** and its **MCP integration** (the same one
  this assistant is connected to). Core capabilities: `generate_image`,
  `generate_video`, a product-focused **Marketing Studio**, plus
  `upscale_image`, `remove_background`, `reframe`, `outpaint_image`, and a
  `virality_predictor` for scoring creative.
- There is **no first-party "create a Meta campaign" API** here — the bridge to
  ad platforms is: generate asset → download → upload to Ads Manager (manually
  or via the Meta Marketing API if you automate later).

## Realistic connection options (today)

| You want to connect… | Best option |
|----------------------|-------------|
| Shopify event → custom code | Shopify **webhooks** → your server (this repo) |
| No-code glue between apps | **Zapier / Make / n8n** (Shopify, OpenAI/Anthropic, Google Sheets, email) |
| Claude → Shopify | Shopify **Admin GraphQL API** from your script (this repo) |
| Claude/agent → Higgsfield | Higgsfield **MCP** (image/video/marketing-studio tools) |
| Creative → ads | Manual upload now; **Meta Marketing API / Google Ads API** later |

Start with webhooks + scripts (this repo) for anything custom, and reach for
Make/n8n when you just need to wire two SaaS tools together without code.
