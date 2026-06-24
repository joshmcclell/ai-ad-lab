# 10. UK GDPR & Data Protection Setup

> Practical setup notes, not legal advice. For a real business, confirm specifics
> with the **ICO** (ico.org.uk) and consider a template DPA from a reputable
> source. The platform is *built* to make compliance easy — these are the steps
> to actually be compliant.

## Your role: you are a **data processor**

Your clients (the businesses using FlowBase) are **data controllers** of their
customers' data; **you process it on their behalf**. That means:

- [ ] **Register with the ICO** as a data controller/processor (~£40–£60/year fee
      for most small businesses — this is a legal fee, separate from tech costs).
- [ ] **Sign a Data Processing Agreement (DPA)** with each client. Provide a
      standard DPA as part of onboarding (template once, reuse).
- [ ] **Keep a Record of Processing Activities (ROPA)** — what data, why, where.

## How the build supports the 7 GDPR principles

| Principle | Where it's handled |
|-----------|--------------------|
| Lawful basis & consent | `contacts.lawful_basis`, `consent_marketing`, `consent_source`, `consent_at` captured at lead intake (W1) |
| Purpose limitation | Data only used for the client's CRM; isolated per tenant |
| Data minimisation | Only the fields in `db/schema.sql`; custom fields are opt-in |
| Accuracy | Contacts editable; `updated_at` tracked |
| Storage limitation | `data_retention_policies` + the `apply_retention()` sweep (W7, `db/functions.sql`), scheduled nightly via `db/schedule.sql` |
| Integrity & confidentiality | Tenant isolation via RLS (`db/policies.sql`); roles; verified backups (`db/backup.sh`, W8) |
| Accountability | `audit_log` records create/update/delete/export/login |

## Data subject rights — how you fulfil them

- **Right of access (SAR):** export a contact's full record + `activities` +
  `audit_log` (one query/export per `account_id` + `contact_id`).
- **Right to erasure:** soft-delete (`deleted_at`) then hard-delete after grace;
  logged. The retention sweep also handles automatic erasure.
- **Right to rectification:** edit the contact; change is audit-logged.
- **Right to data portability:** the data export (CSV/JSON) in requirement #8.
- **Right to object / withdraw consent:** flip `consent_marketing=false`; future
  automations skip the contact.

## Concrete setup checklist
- [ ] Add a consent checkbox to every lead-capture form (records `consent_source`).
- [ ] `data_retention_policies` are created automatically by `provision_account()`
      (contact = 3yr anonymise, activity = 2yr delete — adjust per client).
- [ ] Schedule the retention sweep: `db/schedule.sql` (pg_cron) or the
      `n8n/W7-retention-sweep.json` workflow. Verify with `select * from apply_retention();`.
- [ ] Schedule backups: `db/backup.sh` from cron / a GitHub Action / n8n.
- [ ] Enable `audit_log` writes in every create/update/delete workflow.
- [ ] Store backups encrypted, in the **UK/EU region** where possible
      (Supabase EU region; Backblaze/B2 EU bucket).
- [ ] Write a short **Privacy Policy** and **DPA** for FlowBase; link from signup.
- [ ] Have a breach-notification plan (ICO requires reporting within 72 hours).
- [ ] Keep data in UK/EU regions to avoid international-transfer complications.

## Data residency
Pick EU/UK regions when creating Supabase, storage buckets, and email (Brevo EU).
This keeps you clear of international data-transfer rules by default.
