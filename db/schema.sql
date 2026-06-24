-- =============================================================================
-- FlowBase CRM — PostgreSQL schema (open-source build path)
-- =============================================================================
-- Multi-tenant SaaS. Each paying client = one row in `accounts` (a tenant).
-- All tenant data carries account_id and is isolated by Row-Level Security (RLS).
-- Target: PostgreSQL 14+ (works on Supabase free tier and any self-hosted PG).
--
-- Apply with:  psql "$DATABASE_URL" -f db/schema.sql
-- Then seed:   psql "$DATABASE_URL" -f db/seed.sql
-- RLS policy examples live in db/policies.sql (enable when using Supabase Auth).
-- =============================================================================

create extension if not exists "pgcrypto";   -- gen_random_uuid()
create extension if not exists "citext";      -- case-insensitive email

-- ----------------------------------------------------------------------------
-- Enums
-- ----------------------------------------------------------------------------
do $$ begin
  create type account_status   as enum ('trialing','active','past_due','paused','cancelled');
  create type sub_status        as enum ('approval_pending','active','suspended','past_due','cancelled','expired');
  create type payment_status    as enum ('completed','pending','failed','refunded');
  create type user_role         as enum ('owner','admin','manager','agent','viewer');
  create type contact_kind      as enum ('lead','contact','customer');
  create type activity_type     as enum ('email','call','note','meeting','sms','task_log');
  create type activity_dir      as enum ('inbound','outbound','internal');
  create type task_status       as enum ('open','done','cancelled');
  create type deal_status       as enum ('open','won','lost');
  create type lawful_basis      as enum ('consent','contract','legal_obligation','vital_interests','public_task','legitimate_interests');
  create type retention_action  as enum ('anonymize','delete');
exception when duplicate_object then null; end $$;

-- ----------------------------------------------------------------------------
-- Tenants (one per paying client) + billing
-- ----------------------------------------------------------------------------
create table if not exists accounts (
  id                 uuid primary key default gen_random_uuid(),
  name               text not null,
  slug               citext unique,
  status             account_status not null default 'trialing',
  plan_price_pennies integer not null default 9900,        -- £99.00
  plan_currency      char(3) not null default 'GBP',
  trial_ends_at      timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create table if not exists subscriptions (
  id                     uuid primary key default gen_random_uuid(),
  account_id             uuid not null references accounts(id) on delete cascade,
  provider               text not null default 'paypal',
  paypal_subscription_id text unique,                       -- e.g. I-XXXXXXXXXXXX
  paypal_plan_id         text,                              -- e.g. P-XXXXXXXXXXXX
  status                 sub_status not null default 'approval_pending',
  current_period_start   timestamptz,
  current_period_end     timestamptz,
  last_payment_at        timestamptz,
  last_payment_pennies   integer,
  next_billing_at        timestamptz,
  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now()
);
create index if not exists idx_subscriptions_account on subscriptions(account_id);

-- Immutable-ish ledger of every PayPal money movement (audit + reconciliation)
create table if not exists payments (
  id                uuid primary key default gen_random_uuid(),
  account_id        uuid not null references accounts(id) on delete cascade,
  subscription_id   uuid references subscriptions(id) on delete set null,
  paypal_txn_id     text unique,                            -- sale/capture id
  amount_pennies    integer not null,
  currency          char(3) not null default 'GBP',
  status            payment_status not null,
  paid_at           timestamptz,
  raw               jsonb,                                  -- full webhook payload
  created_at        timestamptz not null default now()
);
create index if not exists idx_payments_account on payments(account_id, paid_at desc);

-- ----------------------------------------------------------------------------
-- Users, roles & access
-- account_id NULL  => platform super-admin (you, the operator)
-- ----------------------------------------------------------------------------
create table if not exists users (
  id                uuid primary key default gen_random_uuid(),
  account_id        uuid references accounts(id) on delete cascade,
  auth_uid          uuid,                                   -- maps to Supabase auth.users.id
  email             citext not null unique,
  full_name         text,
  role              user_role not null default 'agent',
  is_platform_admin boolean not null default false,
  is_active         boolean not null default true,
  last_seen_at      timestamptz,
  created_at        timestamptz not null default now()
);
create index if not exists idx_users_account on users(account_id);

-- ----------------------------------------------------------------------------
-- Contacts / leads
-- ----------------------------------------------------------------------------
create table if not exists contacts (
  id                uuid primary key default gen_random_uuid(),
  account_id        uuid not null references accounts(id) on delete cascade,
  kind              contact_kind not null default 'lead',
  first_name        text,
  last_name         text,
  email             citext,
  phone             text,
  company           text,
  job_title         text,
  source            text,                                   -- e.g. "Website form", "Referral"
  owner_user_id     uuid references users(id) on delete set null,
  -- GDPR fields
  consent_marketing boolean not null default false,
  consent_source    text,
  consent_at        timestamptz,
  lawful_basis      lawful_basis,
  -- housekeeping
  last_activity_at  timestamptz,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  deleted_at        timestamptz                              -- soft delete for retention
);
create index if not exists idx_contacts_account on contacts(account_id) where deleted_at is null;
create index if not exists idx_contacts_email   on contacts(account_id, email);
create index if not exists idx_contacts_owner   on contacts(owner_user_id);

create table if not exists tags (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references accounts(id) on delete cascade,
  name        text not null,
  color       text default '#2563eb',
  unique (account_id, name)
);

create table if not exists contact_tags (
  contact_id  uuid not null references contacts(id) on delete cascade,
  tag_id      uuid not null references tags(id) on delete cascade,
  primary key (contact_id, tag_id)
);

-- Custom fields: definitions + values (EAV, scoped per tenant + entity)
create table if not exists custom_fields (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references accounts(id) on delete cascade,
  entity      text not null check (entity in ('contact','deal')),
  key         text not null,
  label       text not null,
  field_type  text not null check (field_type in ('text','number','date','boolean','select','url','email')),
  options     jsonb,                                         -- for select types
  position    integer not null default 0,
  unique (account_id, entity, key)
);

create table if not exists custom_field_values (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references accounts(id) on delete cascade,
  field_id    uuid not null references custom_fields(id) on delete cascade,
  entity      text not null,
  record_id   uuid not null,
  value       jsonb,
  unique (field_id, record_id)
);

-- ----------------------------------------------------------------------------
-- Pipelines / stages / deals
-- ----------------------------------------------------------------------------
create table if not exists pipelines (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references accounts(id) on delete cascade,
  name        text not null,
  is_default  boolean not null default false,
  created_at  timestamptz not null default now()
);

create table if not exists stages (
  id           uuid primary key default gen_random_uuid(),
  account_id   uuid not null references accounts(id) on delete cascade,
  pipeline_id  uuid not null references pipelines(id) on delete cascade,
  name         text not null,
  position     integer not null default 0,
  probability  integer not null default 0 check (probability between 0 and 100),
  is_won       boolean not null default false,
  is_lost      boolean not null default false,
  unique (pipeline_id, name)
);
create index if not exists idx_stages_pipeline on stages(pipeline_id, position);

create table if not exists deals (
  id                  uuid primary key default gen_random_uuid(),
  account_id          uuid not null references accounts(id) on delete cascade,
  pipeline_id         uuid not null references pipelines(id) on delete cascade,
  stage_id            uuid not null references stages(id),
  contact_id          uuid references contacts(id) on delete set null,
  title               text not null,
  value_pennies       integer not null default 0,
  currency            char(3) not null default 'GBP',
  status              deal_status not null default 'open',
  owner_user_id       uuid references users(id) on delete set null,
  expected_close_date date,
  closed_at           timestamptz,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now()
);
create index if not exists idx_deals_account on deals(account_id, status);
create index if not exists idx_deals_stage   on deals(stage_id);

-- ----------------------------------------------------------------------------
-- Communication log + tasks/reminders + calendar
-- ----------------------------------------------------------------------------
create table if not exists activities (
  id           uuid primary key default gen_random_uuid(),
  account_id   uuid not null references accounts(id) on delete cascade,
  contact_id   uuid references contacts(id) on delete cascade,
  deal_id      uuid references deals(id) on delete cascade,
  user_id      uuid references users(id) on delete set null,
  type         activity_type not null,
  direction    activity_dir not null default 'outbound',
  subject      text,
  body         text,
  occurred_at  timestamptz not null default now(),
  created_at   timestamptz not null default now()
);
create index if not exists idx_activities_contact on activities(contact_id, occurred_at desc);
create index if not exists idx_activities_account on activities(account_id, occurred_at desc);

create table if not exists tasks (
  id               uuid primary key default gen_random_uuid(),
  account_id       uuid not null references accounts(id) on delete cascade,
  contact_id       uuid references contacts(id) on delete cascade,
  deal_id          uuid references deals(id) on delete cascade,
  assigned_user_id uuid references users(id) on delete set null,
  title            text not null,
  description      text,
  due_at           timestamptz,
  remind_at        timestamptz,
  status           task_status not null default 'open',
  created_at       timestamptz not null default now(),
  completed_at     timestamptz
);
create index if not exists idx_tasks_due on tasks(account_id, status, due_at);

create table if not exists calendar_events (
  id           uuid primary key default gen_random_uuid(),
  account_id   uuid not null references accounts(id) on delete cascade,
  user_id      uuid references users(id) on delete set null,
  contact_id   uuid references contacts(id) on delete set null,
  external_id  text,                                         -- Cal.com / Google event id
  title        text,
  starts_at    timestamptz,
  ends_at      timestamptz,
  created_at   timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- Audit trail + data-retention policy (GDPR)
-- ----------------------------------------------------------------------------
create table if not exists audit_log (
  id            bigint generated always as identity primary key,
  account_id    uuid references accounts(id) on delete cascade,
  actor_user_id uuid references users(id) on delete set null,
  action        text not null,                              -- create/update/delete/export/login
  entity        text,
  record_id     uuid,
  changes       jsonb,
  ip_address    inet,
  created_at    timestamptz not null default now()
);
create index if not exists idx_audit_account on audit_log(account_id, created_at desc);

create table if not exists data_retention_policies (
  id          uuid primary key default gen_random_uuid(),
  account_id  uuid not null references accounts(id) on delete cascade,
  entity      text not null,                                -- 'contact','activity', ...
  retain_days integer not null,                             -- after last_activity / occurred_at
  action      retention_action not null default 'anonymize',
  is_active   boolean not null default true,
  unique (account_id, entity)
);

-- ----------------------------------------------------------------------------
-- Dashboard views (real-time reporting)
-- ----------------------------------------------------------------------------
create or replace view v_pipeline_value as
select d.account_id,
       d.pipeline_id,
       d.stage_id,
       s.name as stage_name,
       count(*) filter (where d.status = 'open')                as open_deals,
       coalesce(sum(d.value_pennies) filter (where d.status='open'),0) as open_value_pennies
from deals d
join stages s on s.id = d.stage_id
group by d.account_id, d.pipeline_id, d.stage_id, s.name;

create or replace view v_conversion as
select account_id,
       count(*) filter (where status='won')  as won,
       count(*) filter (where status='lost') as lost,
       count(*) filter (where status in ('won','lost')) as closed,
       round(
         100.0 * count(*) filter (where status='won')
         / nullif(count(*) filter (where status in ('won','lost')),0), 1
       ) as win_rate_pct
from deals
group by account_id;

create or replace view v_activity_daily as
select account_id,
       date_trunc('day', occurred_at)::date as day,
       type,
       count(*) as n
from activities
group by account_id, date_trunc('day', occurred_at), type;

-- ----------------------------------------------------------------------------
-- updated_at trigger
-- ----------------------------------------------------------------------------
create or replace function set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

do $$
declare t text;
begin
  foreach t in array array['accounts','subscriptions','contacts','deals'] loop
    execute format(
      'drop trigger if exists trg_updated_%1$s on %1$s;
       create trigger trg_updated_%1$s before update on %1$s
       for each row execute function set_updated_at();', t);
  end loop;
end $$;
