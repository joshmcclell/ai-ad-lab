# n8n Workflows

Importable starting points for the automations described in
`../docs/04-workflows-automation.md`. Import via **n8n → Workflows → Import from
File**, then set credentials and activate.

## What's here

| File | Workflow | Trigger |
|------|----------|---------|
| `W1-lead-intake.json` | New lead → contact + 24h follow-up task + welcome email | Webhook `POST /flowbase-lead` |
| `W3-task-reminders.json` | Email task owners when a reminder is due | Schedule (every 15 min) |

The other workflows (W2, W4, W7, W8, W9) are specified step-by-step in
`../docs/04-workflows-automation.md` and follow the same shape — add them the
same way as you need them.

## Before they run — required setup

1. **Postgres credential.** Create one n8n Postgres credential pointing at your
   Supabase/Postgres database and name it `FlowBase Postgres`. Each node's
   `credentials.postgres.id` shows `REPLACE` — n8n lets you pick the real
   credential on import.
2. **Environment variables** in n8n: `BREVO_API_KEY` for email sending.
3. **Sender address.** Replace `hello@flowbasecrm.com` with your verified Brevo
   sender.
4. **Webhook payload (W1).** The lead form must POST JSON including `account_id`
   (the tenant), plus `first_name`, `last_name`, `email`, and optionally
   `phone`, `company`, `source`, `consent`.

## Why PayPal isn't here

Billing (W5/W6) is handled in the app itself at
`../app/src/app/api/paypal/webhook/route.ts` so signature verification and the
service-role DB writes live in one trusted place. If you prefer to run it in n8n
instead, replicate that logic in a webhook workflow.

> These JSON files are scaffolds: valid to import, but credentials, the exact
> Postgres node `typeVersion`, and sender details depend on your n8n version and
> environment. Review each node after import.
