# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This repo holds **FlowBase CRM** — the blueprint and build artifacts for a
£99/month managed multi-tenant CRM service (a simplified HubSpot/Salesforce
alternative) designed to run on free tiers and open-source software, with billing
via PayPal recurring subscriptions.

It is **documentation + database artifacts + a runnable application**. Start at
`README.md`, which indexes everything.

## Layout

- `docs/01..11-*.md` — the business and technical design, numbered in reading
  order (branding → tech stack → data model → workflows → setup guides → PayPal →
  service summary → onboarding → GDPR → scaling).
- `db/schema.sql` — PostgreSQL schema; the multi-tenant backbone.
- `db/seed.sql` — demo tenant, default pipeline/stages, sample records.
- `db/functions.sql` — server-side functions; notably `provision_account()`,
  the atomic "add a client" routine.
- `db/policies.sql` — Row-Level Security policies for tenant isolation.
- `db/test/` — integration test harness (`run-tests.sh` + `assertions.sql`).
- `app/` — the Next.js 14 (App Router) + Supabase application implementing the
  open-source build path, including the PayPal billing webhook and operator console.
- `n8n/` — importable automation workflow JSON (lead intake, task reminders).

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
psql "$DATABASE_URL" -f db/functions.sql  # provision_account(), etc.
psql "$DATABASE_URL" -f db/policies.sql   # RLS; works on Supabase and plain PG
```

To validate changes, run the integration tests — they spin up a throwaway
Postgres, apply all four files (seed twice, to prove idempotency), and assert
seed/provisioning/RLS invariants:

```bash
db/test/run-tests.sh        # exits non-zero on the first failed assertion
```

The harness must run as a non-root user (it re-execs as `postgres` if root) and
keeps the Unix socket dir short (<100 chars). Add new invariants to
`db/test/assertions.sql` (each check RAISEs on failure under `ON_ERROR_STOP=1`).

**New tenants are created via `provision_account(name, email, ...)`** — never by
hand-inserting an `accounts` row, which would skip the default pipeline, stages,
retention policies, and owner user. The PayPal webhook and the operator console
both call it; keep it the single provisioning path.

Conventions in the schema:
- Money is stored in integer **pennies** (`*_pennies`), currency in `char(3)`
  (`GBP`).
- Soft-delete via `deleted_at` (contacts) for GDPR retention; hard-delete after a
  grace period.
- Seed uses fixed UUIDs + `ON CONFLICT` so it is idempotent — preserve that when
  adding seed rows (every table you seed needs a unique key to conflict on).
- Dashboards read the `v_pipeline_value`, `v_conversion`, `v_activity_daily`
  views — extend these rather than computing metrics ad hoc.

## Working with the application (`app/`)

Commands (run from `app/`):

```bash
npm install
npm run dev         # local dev server on :3000
npm run build       # production build — must pass
npm run typecheck   # tsc --noEmit — must pass
npm run lint        # next lint
```

There is no automated test suite yet; `build` + `typecheck` are the gate. Both
currently pass.

Architecture rules that matter:
- **Three Supabase clients, used deliberately** (`src/lib/supabase/`):
  `server.ts` (RSC/server actions, RLS-scoped to the signed-in user),
  `client.ts` (browser, RLS-scoped), and `admin.ts` (service-role, **bypasses
  RLS**). `admin.ts` is for trusted server-only cross-tenant writes — currently
  just the PayPal webhook. Never import `admin.ts` into a client component or a
  normal user-facing query; doing so would break tenant isolation.
- **Auth + tenant scoping is implicit.** Because RLS is enabled, server/client
  components just query their table and get only their tenant's rows. Don't add
  manual `account_id` filters expecting them to be the security boundary — RLS is.
- `src/middleware.ts` refreshes the session and redirects unauthenticated users
  to `/login` (public paths: `/login`, `/auth`, `/api/paypal`).
- **The PayPal webhook** (`src/app/api/paypal/webhook/route.ts`) must verify the
  signature before any DB write and is idempotent on the PayPal txn id. It mirrors
  workflows W5/W6 — keep it in sync with `docs/07` if you change billing logic.
- `src/lib/types.ts` mirrors `db/schema.sql` by hand (no codegen). If you change
  the schema, update these types too.
- Money is integer pennies everywhere; format via `src/lib/format.ts`.
- **Next.js version:** pinned to 14.2.35. `npm audit` flags advisories fixed only
  in Next 15/16 (a breaking upgrade — 15+ makes `cookies()`/`headers()` async).
  See `app/README.md` before bumping the major.

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
