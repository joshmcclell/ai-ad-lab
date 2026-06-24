# 4. Workflows & Automation

These are the automations that keep your daily workload near zero. Each is
described as a trigger → steps recipe you can build in **n8n** (Path B / free
self-host) or **Make** (Path A / free tier). Node names match n8n.

> Convention: every workflow first resolves the `account_id` so it only ever
> touches the right tenant's data.

---

## W1 — New lead intake
**Trigger:** Webhook (lead form submit) or new row in `contacts`.
**Steps:**
1. Webhook → validate required fields (name, email).
2. Upsert `contacts` row (`kind='lead'`, `source` from form, consent fields from
   the opt-in checkbox).
3. Set `owner_user_id` (round-robin or fixed).
4. Create a `tasks` row: "Follow up with {{name}}", `due_at = now + 24h`.
5. Send welcome email via Brevo.
6. Write `audit_log` (`action='create'`, `entity='contact'`).

## W2 — Pipeline stage change
**Trigger:** `deals.stage_id` changes (DB trigger / polling / NocoDB webhook).
**Steps:**
1. Insert `activities` row (`type='note'`, "Moved to {{stage}}").
2. If new stage `is_won` → set `deals.status='won'`, `closed_at=now()`,
   convert `contacts.kind` to `customer`.
3. If `is_lost` → `status='lost'`, log reason.
4. Optional: send templated email for specific stages (e.g. "Proposal Sent").

## W3 — Task reminders & follow-ups
**Trigger:** Schedule (every 15 min).
**Steps:**
1. Query `tasks` where `status='open'` and `remind_at <= now()` (or `due_at` soon).
2. For each, email/Slack the `assigned_user_id`.
3. Mark a `reminded_at` flag (add column or use a tag) to avoid duplicates.

## W4 — Calendar sync
**Trigger:** Cal.com webhook (booking created/updated/cancelled).
**Steps:**
1. Upsert `calendar_events` (`external_id`, `starts_at`, `ends_at`, `contact_id`).
2. Create a `tasks`/`activities` entry so the meeting shows in the contact timeline.

## W5 — PayPal payment received  *(money workflow — see `07-paypal-integration.md`)*
**Trigger:** PayPal webhook `PAYMENT.SALE.COMPLETED` / `BILLING.SUBSCRIPTION.ACTIVATED`.
**Steps:**
1. Verify webhook signature (PayPal `verify-webhook-signature`).
2. Find `subscriptions` by `paypal_subscription_id`.
3. Insert `payments` row (amount, txn id, `status='completed'`, store `raw`).
4. Update `subscriptions` (`status='active'`, `last_payment_at`, `current_period_end`, `next_billing_at`).
5. Set parent `accounts.status='active'`.
6. Email the client a receipt; notify you of the new active client.

## W6 — PayPal payment failed / subscription cancelled
**Trigger:** `BILLING.SUBSCRIPTION.PAYMENT.FAILED`, `...SUSPENDED`, `...CANCELLED`.
**Steps:**
1. Update `subscriptions.status` accordingly.
2. Set `accounts.status='past_due'` (failed) or `'cancelled'`.
3. Alert you (email/Slack) + optional dunning email to the client.

## W7 — Nightly data-retention sweep  *(GDPR — see `10-gdpr-uk.md`)*
**Built.** Implemented as the `apply_retention()` function in `db/functions.sql`
and covered by the test harness (T5). It walks every active row in
`data_retention_policies` and: anonymises (strips PII, keeps the row) or
soft-deletes contacts past `retain_days`, deletes/anonymises old `activities`,
and writes a summary to `audit_log`. It is idempotent.
**Schedule it** either way:
- **In-database (Supabase):** `db/schedule.sql` registers a nightly pg_cron job.
- **Via n8n:** import `n8n/W7-retention-sweep.json` (schedule → `select apply_retention();`).
Run on demand any time with `select * from apply_retention();`.

## W8 — Nightly backup & export  *(requirement #8)*
**Built.** `db/backup.sh` takes a portable, gzipped `pg_dump` and rotates old
backups (verified: produces a dump that restores cleanly into a fresh database).
**Trigger:** Schedule (daily 03:00) from any external scheduler — cron on a free
VM, a GitHub Action, or an n8n *Execute Command* node (pg_dump needs shell
access, so it can't run inside Supabase/pg_cron).
**Steps:**
1. `DATABASE_URL=… BACKUP_DIR=… db/backup.sh` writes `flowbase-<ts>.sql.gz`.
2. Sync `BACKUP_DIR` to free off-site storage (Backblaze B2 10 GB free / Supabase
   Storage / Google Drive) with rclone. Keep 7–30 days (`BACKUP_RETAIN_DAYS`).
- **Path A (no-code):** scheduled CSV/Excel export of each NocoDB table → same storage.
- Restore: `gunzip -c <file> | psql "$DATABASE_URL"`.

## W9 — Monthly billing reconciliation
**Trigger:** Schedule (daily).
**Steps:**
1. Find `subscriptions` whose `current_period_end < now()` but no recent payment.
2. Flag `accounts.status='past_due'` and alert you — catches silent PayPal failures
   the webhooks didn't deliver.

---

### Build order (do these first)
W5 + W6 (get paid & track it) → W1 (capture leads) → W3 (never miss follow-ups)
→ W8 (backups) → W7 (GDPR). W2/W4/W9 are quality-of-life, add after launch.
