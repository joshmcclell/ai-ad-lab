# 3. Database / Field Structure & Workflow Design

The authoritative schema is **`db/schema.sql`** (PostgreSQL). This page explains
it in plain English and maps it onto the no-code tools if you build Path A.

## Core idea: one platform, many isolated tenants

Every client business is an **`account`** (a tenant). Every record (contact,
deal, task…) carries an `account_id`, and Row-Level Security (`db/policies.sql`)
guarantees one client can never see another's data. You — the operator — are a
**platform super-admin** who can see across all tenants for support.

## Tables & key fields

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `accounts` | One per paying client (tenant) | `name`, `status` (trialing/active/past_due/paused/cancelled), `plan_price_pennies` (9900) |
| `subscriptions` | PayPal billing link per account | `paypal_subscription_id`, `status`, `current_period_end`, `next_billing_at` |
| `payments` | Ledger of every PayPal payment | `paypal_txn_id`, `amount_pennies`, `status`, `paid_at`, `raw` (webhook JSON) |
| `users` | People who log in | `role` (owner/admin/manager/agent/viewer), `is_platform_admin`, `account_id` |
| `contacts` | Leads & customers | `kind`, name/email/phone/company, `source`, `owner_user_id`, **GDPR**: `consent_marketing`, `consent_at`, `lawful_basis`, `deleted_at` |
| `tags` + `contact_tags` | Free-form labels | `name`, `color` |
| `custom_fields` + `custom_field_values` | Per-tenant custom fields | `entity`, `key`, `field_type`, `options` |
| `pipelines` / `stages` | Customisable boards | stage `position`, `probability`, `is_won`, `is_lost` |
| `deals` | Opportunities with value | `value_pennies`, `stage_id`, `status`, `expected_close_date` |
| `activities` | Central comms log | `type` (email/call/note/meeting/sms), `direction`, `subject`, `body`, `occurred_at` |
| `tasks` | Follow-ups & reminders | `due_at`, `remind_at`, `status`, `assigned_user_id` |
| `calendar_events` | Cal.com/Google sync | `external_id`, `starts_at`, `ends_at` |
| `audit_log` | GDPR audit trail | `action`, `entity`, `record_id`, `changes`, `actor_user_id` |
| `data_retention_policies` | Auto-cleanup rules | `entity`, `retain_days`, `action` (anonymize/delete) |

### Reporting views (real-time dashboards)
- `v_pipeline_value` — open deal count & value per stage
- `v_conversion` — won/lost/win-rate per account
- `v_activity_daily` — activity volume per day by type

## User roles (requirement #7)

| Role | Can do |
|------|--------|
| `owner` | Everything in the account, incl. billing & user management |
| `admin` | Everything except delete the account |
| `manager` | All records + reports; manage agents' work |
| `agent` | Create/edit own + assigned records; no settings |
| `viewer` | Read-only |
| platform super-admin (`is_platform_admin`) | Cross-tenant support access (you) |

In Path B these map directly to Supabase RLS. In Path A (NocoDB) they map to
NocoDB's workspace roles (Owner/Creator/Editor/Commenter/Viewer).

## Mapping to the no-code build (Path A)

Each SQL table becomes a **NocoDB/Baserow table** with the same columns. The
EAV `custom_fields` pattern isn't needed in no-code — you just add columns to the
`contacts`/`deals` tables directly per client base. Pipelines become a **Kanban
view** of the `deals` table grouped by a single-select `stage` field.

## Workflow design (the automation backbone)

The data model is designed so these automations are trivial to wire up (full
step-by-step in `04-workflows-automation.md`):

1. **New lead → contact created → owner assigned → "follow up in 24h" task.**
2. **Deal moves stage → log activity + (optional) trigger templated email.**
3. **Task due / `remind_at` reached → reminder email/Slack to the owner.**
4. **PayPal payment received → `payments` row + set `account.status='active'`.**
5. **PayPal payment failed/cancelled → `account.status='past_due'` + alert you.**
6. **Nightly retention job → anonymise/delete records past `retain_days`.**
7. **Nightly backup → export all tables to storage.**
