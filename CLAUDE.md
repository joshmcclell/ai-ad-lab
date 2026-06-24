# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This repo holds **FlowBase CRM** — the blueprint and build artifacts for a
£99/month managed multi-tenant CRM service (a simplified HubSpot/Salesforce
alternative) designed to run on free tiers and open-source software, with billing
via PayPal recurring subscriptions.

It is **documentation + database artifacts**, not a running application. There is
no app server or test suite in the repo yet — the runnable parts are SQL files.
Start at `README.md`, which indexes everything.

## Layout

- `docs/01..11-*.md` — the business and technical design, numbered in reading
  order (branding → tech stack → data model → workflows → setup guides → PayPal →
  service summary → onboarding → GDPR → scaling).
- `db/schema.sql` — PostgreSQL schema; the multi-tenant backbone.
- `db/seed.sql` — demo tenant, default pipeline/stages, sample records.
- `db/policies.sql` — Row-Level Security policies for tenant isolation.

## Core architecture (read before changing `db/`)

- **Multi-tenant SaaS.** Each paying client is one row in `accounts` (a tenant).
  Every tenant-scoped table carries `account_id`. Tenant data is isolated by
  Row-Level Security in `db/policies.sql` — do not add a tenant table without an
  `account_id` column and a matching policy.
- **The operator is a platform super-admin** (`users.is_platform_admin = true`,
  `account_id` NULL) and can see across tenants for support.
- **RLS identity resolution must not recurse.** `current_account_id()` and
  `is_super_admin()` query the `users` table, which is itself RLS-protected, so
  they are declared `SECURITY DEFINER` to bypass RLS. Keep that — removing it
  causes infinite recursion (verified failure mode).
- **`policies.sql` is portable.** On Supabase it uses the native `auth.uid()`. On
  plain Postgres a shim creates `auth.uid()` reading the GUC `app.current_user_id`
  (set per session with `SET app.current_user_id = '<users.auth_uid>'`).
- **Two build paths** (`docs/02-tech-stack.md`): No-code (NocoDB/Make/Cal.com) and
  Open-source (Supabase/Next.js/n8n). The SQL targets the open-source path; the
  no-code path mirrors the same tables/fields.
- **Money + automation flow through webhooks.** PayPal webhooks drive
  subscription/payment status (`docs/07`, workflows W5/W6 in `docs/04`). A daily
  reconciliation job (W9) is the safety net for undelivered webhooks.

## Working with the database SQL

Apply in this order (the only "build/run" in the repo):

```bash
psql "$DATABASE_URL" -f db/schema.sql
psql "$DATABASE_URL" -f db/seed.sql       # idempotent — safe to re-run
psql "$DATABASE_URL" -f db/policies.sql   # RLS; works on Supabase and plain PG
```

To validate changes locally without a server account, run a throwaway Postgres
(must run as a non-root user, e.g. `su postgres -c ...`; Unix socket dirs must be
short, under ~100 chars) and apply the three files with `-v ON_ERROR_STOP=1`.

Conventions in the schema:
- Money is stored in integer **pennies** (`*_pennies`), currency in `char(3)`
  (`GBP`).
- Soft-delete via `deleted_at` (contacts) for GDPR retention; hard-delete after a
  grace period.
- Seed uses fixed UUIDs + `ON CONFLICT` so it is idempotent — preserve that when
  adding seed rows (every table you seed needs a unique key to conflict on).
- Dashboards read the `v_pipeline_value`, `v_conversion`, `v_activity_daily`
  views — extend these rather than computing metrics ad hoc.

## Conventions for the docs

- Keep the numeric ordering and cross-references (docs reference each other and
  the `db/` files by path) intact when editing.
- Be honest about "£0 forever": the docs explicitly call out PayPal per-transaction
  fees, the optional ~£10/yr domain, and free-tier ceilings. Don't quietly drop
  those caveats.

## Git workflow

- Default branch is `main`; develop on `claude/<topic>` branches, never commit
  directly to `main`.
- Push with `git push -u origin <branch-name>`.
- Do not open a pull request unless explicitly asked.
