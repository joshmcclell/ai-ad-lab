# ai-ad-lab

A practical starter kit and playbook for running an **AI-assisted dropshipping
business** built on three tools:

| Tool | Role in the business |
|------|----------------------|
| **Shopify** | Storefront, product catalog, checkout, payments, orders, customer data. The system of record. |
| **Claude** (`claude-opus-4-8`) | The "brain": market research, product copy, blog content, email sequences, ad copy, and the automation logic that glues everything together. |
| **Higgsfield** | The "studio": AI-generated ad visuals (images/video), product shots, and performance-tested creative. |

> ⚠️ **Important framing.** Higgsfield is a *creative generation* platform
> (images, video, a "Marketing Studio" for product ads). It does **not** run or
> buy ads for you. The actual ad delivery still happens on **Meta Ads Manager,
> Google Ads, or TikTok Ads**. This repo treats Higgsfield as the creative
> engine and the ad platforms as the delivery layer. See
> [`docs/architecture.md`](docs/architecture.md).

---

## What's in here

```
ai-ad-lab/
├── README.md                  ← you are here (overview + roadmap)
├── .env.example               ← all secrets/config in one place
├── package.json
├── src/
│   ├── claudeClient.ts        ← thin wrapper around the Anthropic SDK
│   ├── shopifyClient.ts       ← thin wrapper around the Shopify Admin GraphQL API
│   ├── generateProductContent.ts  ← Claude → structured product copy → Shopify
│   ├── generateAdCopy.ts      ← Claude → ad headlines/body for a product
│   └── webhookServer.ts       ← receives Shopify webhooks (orders, products)
└── docs/
    ├── architecture.md        ← how the three tools fit together + data flow
    ├── workflows.md           ← step-by-step automation recipes
    ├── compliance-uk-eu.md    ← UK/EU legal + advertising checklist
    └── roadmap.md             ← launch → scale plan
```

---

## Quick start

```bash
# 1. Install dependencies (Node 18+ required for global fetch)
npm install

# 2. Copy the env template and fill in your keys
cp .env.example .env

# 3. Generate product copy for one product and push it to Shopify
npm run product -- "Adjustable laptop stand, aluminium, foldable"

# 4. Generate ad copy for the same product
npm run adcopy -- "Adjustable laptop stand, aluminium, foldable"

# 5. Run the webhook server locally (use ngrok/cloudflared to expose it)
npm run server
```

You do **not** need every key to start — the product/ad-copy scripts only need
`ANTHROPIC_API_KEY` plus the Shopify keys.

---

## Recommended setup order

1. **Shopify store skeleton** — theme, policies, payments, shipping. (No code yet.)
2. **Claude API** — get an API key, run `npm run product` to confirm copy generation works.
3. **Higgsfield** — generate your first product/ad visuals (via the Higgsfield app or its MCP).
4. **Ad accounts** — Meta Business + Google Ads, with the pixel/tag installed on Shopify.
5. **Glue/automation** — webhook server + scheduled jobs (this repo).

Full reasoning for the order is in [`docs/roadmap.md`](docs/roadmap.md).

---

## The 60-second mental model

```
   ┌─────────────┐   product idea    ┌─────────────┐
   │   Claude    │ ───────────────▶  │  Higgsfield │  (visuals + video)
   │  (copy +    │ ◀───────────────  │  (creative) │
   │  strategy)  │   ad copy/brief    └──────┬──────┘
   └──────┬──────┘                           │ creative assets
          │ product copy, SEO, blogs,        ▼
          │ emails                    ┌───────────────┐
          ▼                           │  Meta / Google │  ← ads actually run here
   ┌─────────────┐   orders/webhooks  │   /TikTok Ads  │
   │   Shopify   │ ◀───────────────── └───────┬────────┘
   │ (store +    │                            │ traffic
   │  checkout)  │ ◀──────────────────────────┘
   └─────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for the detailed flow,
APIs, and webhooks.
