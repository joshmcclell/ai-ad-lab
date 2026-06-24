# 2. Tech Stack (all free)

Two build paths are provided. **Pick one to launch** — you don't need both.
Most operators should launch on the **No-code path** (fastest, lowest
maintenance) and only move to the open-source path if they outgrow free tiers
or want full control.

---

## Path A — No-code (recommended to launch)

Easy to maintain, no servers, mostly point-and-click.

| Job | Tool | Free tier | Notes |
|-----|------|-----------|-------|
| Database + UI + Kanban + forms | **NocoDB Cloud** (or Baserow) | Free workspace | Airtable-style. Gives you tables, grid/Kanban/calendar views, and shareable forms with zero code. Self-hostable later for free. |
| Automation engine | **n8n** (self-host free) or **Make** | n8n: free if self-hosted; Make: 1,000 ops/mo free | Runs every workflow in `04-workflows-automation.md`. n8n self-hosted = unlimited & free. |
| Scheduling + calendar sync | **Cal.com** | Free plan | Booking pages, Google/Outlook calendar sync, reminders. |
| Transactional email | **Brevo** (ex-Sendinblue) | 300 emails/day free | Follow-ups, onboarding, payment receipts. Gmail also works for low volume. |
| Dashboards | **Looker Studio** (Google) | Free | Connect to the database for real-time leads/conversion/pipeline charts. |
| Payments | **PayPal** | Free account; per-transaction fee only | Recurring £99 subscription plan, see `07-paypal-integration.md`. |
| Lead capture forms | NocoDB Forms or **Tally** | Free | Embed on client sites; rows land straight in the DB. |
| Hosting (only if self-hosting n8n/NocoDB) | **Oracle Cloud Always Free**, Railway, Render, or Fly.io | Free tier | A single small VM runs n8n + NocoDB comfortably. |

**Maintenance reality:** NocoDB Cloud + Make + Cal.com is the lowest-effort combo
(nothing to host). Self-hosting n8n/NocoDB removes the only usage caps but adds
~1 VM to look after.

---

## Path B — Open-source (full control, no license fees)

More setup, but unlimited and fully owned. This is what the SQL in `db/` targets.

| Job | Tool | Free tier | Notes |
|-----|------|-----------|-------|
| Database + Auth + API + realtime + roles | **Supabase** | 500 MB DB, 50k MAU free | Postgres + built-in Auth + Row-Level Security (powers tenant isolation & user roles) + auto REST/realtime API. Apply `db/schema.sql` and `db/policies.sql` here. |
| Frontend / dashboards | **Next.js** on **Vercel** | Free (Hobby) | The CRM UI + real-time dashboards. |
| Automation engine | **n8n** (self-hosted) | Free | All workflows; receives PayPal webhooks. |
| Scheduling | **Cal.com** (self-host or cloud free) | Free | Calendar sync + booking. |
| Email | **Brevo** API | 300/day free | Same as Path A. |
| Admin reporting (optional) | **Metabase** or **Grafana** | Free OSS | Pre-built dashboards over Postgres if you don't build them in Next.js. |
| Payments | **PayPal REST API** + webhooks | Free | See `07-paypal-integration.md`. |
| Hosting for n8n/Cal.com | **Oracle Cloud Always Free** VM | Free | Docker Compose runs both. |

---

## Honest notes on "£0 forever"

- **Genuinely free:** the software above has free tiers that comfortably cover a
  launch and the first dozens of clients.
- **PayPal** has no monthly fee but takes a per-transaction cut (typically ~2.9% +
  fixed fee, varies by country) — so you net roughly £95–96 of each £99. This is a
  variable cost paid out of revenue, not a fixed running cost.
- **Optional ~£10/year:** a custom domain (`flowbasecrm.com`) for a professional
  look and email. You can launch on free subdomains (`*.vercel.app`,
  `*.noco.to`) at £0 and add a domain later.
- **Free-tier ceilings to watch:** Supabase 500 MB DB, Brevo 300 emails/day,
  Make 1,000 ops/mo. The scaling doc (`11-scaling.md`) explains when each one
  bites and the free way around it (self-host).
