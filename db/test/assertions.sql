-- =============================================================================
-- FlowBase CRM — integration assertions
-- Run by db/test/run-tests.sh against a throwaway Postgres that already has
-- schema.sql + seed.sql (applied twice) + functions.sql + policies.sql loaded.
-- Each check RAISEs on failure; with `psql -v ON_ERROR_STOP=1` that aborts the
-- run with a non-zero exit, so this doubles as a pass/fail gate.
-- =============================================================================

\echo '== T1: seed is idempotent (applied twice by the harness) =='
do $$
declare n int;
begin
  select count(*) into n from accounts where id = '11111111-1111-1111-1111-111111111111';
  if n <> 1 then raise exception 'T1a: expected 1 demo account, got %', n; end if;

  select count(*) into n from stages where pipeline_id = '44444444-4444-4444-4444-444444444444';
  if n <> 6 then raise exception 'T1b: expected 6 stages after 2x seed, got %', n; end if;

  select count(*) into n from deals where id = '77777777-7777-7777-7777-777777777777';
  if n <> 1 then raise exception 'T1c: expected 1 demo deal, got %', n; end if;

  select count(*) into n from activities where id = '88888888-8888-8888-8888-888888888888';
  if n <> 1 then raise exception 'T1d: expected 1 demo activity, got %', n; end if;
end $$;
\echo '   ok'

\echo '== T2: provision_account stands up a complete tenant =='
do $$
declare
  v_acct uuid;
  n int;
begin
  v_acct := provision_account('Test Client Ltd', 'owner@testclient.co.uk', 'Test Owner');

  select count(*) into n from accounts where id = v_acct and status = 'active';
  if n <> 1 then raise exception 'T2a: account not created active'; end if;

  select count(*) into n from pipelines where account_id = v_acct and is_default;
  if n <> 1 then raise exception 'T2b: expected 1 default pipeline, got %', n; end if;

  select count(*) into n from stages where account_id = v_acct;
  if n <> 6 then raise exception 'T2c: expected 6 stages, got %', n; end if;

  select count(*) into n from data_retention_policies where account_id = v_acct;
  if n <> 2 then raise exception 'T2d: expected 2 retention policies, got %', n; end if;

  select count(*) into n from users where account_id = v_acct and role = 'owner';
  if n <> 1 then raise exception 'T2e: expected 1 owner user, got %', n; end if;
end $$;
\echo '   ok'

\echo '== T3: provision_account rejects bad input and rolls back =='
do $$
declare before_n int; after_n int;
begin
  select count(*) into before_n from accounts;
  begin
    perform provision_account('', 'x@y.co');   -- empty name must fail
    raise exception 'T3a: expected failure on empty name';
  exception
    when others then null;  -- expected
  end;
  select count(*) into after_n from accounts;
  if after_n <> before_n then
    raise exception 'T3b: failed provision left % stray accounts', after_n - before_n;
  end if;
end $$;
\echo '   ok'

\echo '== T4: RLS isolates tenants (non-superuser role + forced RLS) =='
-- Map identities so we can impersonate via the app.current_user_id GUC shim.
update users set auth_uid = '33333333-0000-0000-0000-0000000000aa'
  where email = 'jane@acmeplumbing.co.uk';
update users set auth_uid = '00000000-0000-0000-0000-0000000000ad'
  where is_platform_admin;

-- A second tenant with its own contact, to prove cross-tenant invisibility.
insert into accounts (id, name, slug, status)
  values ('99999999-9999-9999-9999-999999999999', 'Beta Co', 'beta-co', 'active')
  on conflict (id) do nothing;
insert into users (id, account_id, auth_uid, email, role)
  values ('aaaaaaaa-0000-0000-0000-000000000001', '99999999-9999-9999-9999-999999999999',
          'bbbbbbbb-0000-0000-0000-0000000000bb', 'beta@beta.co', 'admin')
  on conflict (id) do nothing;
insert into contacts (account_id, kind, first_name, email)
  select '99999999-9999-9999-9999-999999999999', 'lead', 'BetaPerson', 'beta-person@beta.co'
  where not exists (select 1 from contacts where email = 'beta-person@beta.co');

do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'flowbase_app') then
    create role flowbase_app nologin;
  end if;
end $$;
grant usage on schema public to flowbase_app;
grant select on all tables in schema public to flowbase_app;
alter table contacts force row level security;
alter table users force row level security;

-- Acme tenant user: must see only their own contact.
set role flowbase_app;
set app.current_user_id = '33333333-0000-0000-0000-0000000000aa';
do $$
declare names text;
begin
  select string_agg(first_name, ',' order by first_name) into names from contacts;
  if names is distinct from 'Tom' then
    raise exception 'T4a: Acme user should see only Tom, saw: %', coalesce(names, '(none)');
  end if;
end $$;
reset role;
reset app.current_user_id;

-- Beta tenant user: must see only their own contact.
set role flowbase_app;
set app.current_user_id = 'bbbbbbbb-0000-0000-0000-0000000000bb';
do $$
declare names text;
begin
  select string_agg(first_name, ',' order by first_name) into names from contacts;
  if names is distinct from 'BetaPerson' then
    raise exception 'T4b: Beta user should see only BetaPerson, saw: %', coalesce(names, '(none)');
  end if;
end $$;
reset role;
reset app.current_user_id;

-- Platform super-admin: sees across tenants (>= 2 contacts).
set role flowbase_app;
set app.current_user_id = '00000000-0000-0000-0000-0000000000ad';
do $$
declare n int;
begin
  select count(*) into n from contacts;
  if n < 2 then raise exception 'T4c: super-admin should see all tenants, saw %', n; end if;
end $$;
reset role;
reset app.current_user_id;

-- No identity set: sees nothing.
set role flowbase_app;
do $$
declare n int;
begin
  select count(*) into n from contacts;
  if n <> 0 then raise exception 'T4d: anonymous session should see 0 contacts, saw %', n; end if;
end $$;
reset role;
\echo '   ok'

\echo '== T5: apply_retention enforces GDPR retention policies (W7) =='
-- Acme (demo) seed policies: contact = 1095d anonymize, activity = 730d delete.
-- Seed a stale contact + stale activity (past cutoff) and fresh ones (within).
insert into contacts (id, account_id, kind, first_name, last_name, email, last_activity_at)
values ('cccccccc-0000-0000-0000-000000000001',
        '11111111-1111-1111-1111-111111111111', 'lead', 'StaleLead', 'Old',
        'stale@old.example', now() - interval '4 years')
on conflict (id) do nothing;

insert into contacts (id, account_id, kind, first_name, email, last_activity_at)
values ('cccccccc-0000-0000-0000-000000000002',
        '11111111-1111-1111-1111-111111111111', 'lead', 'FreshLead',
        'fresh@new.example', now())
on conflict (id) do nothing;

insert into activities (id, account_id, contact_id, type, direction, body, occurred_at)
values ('eeeeeeee-0000-0000-0000-000000000001',
        '11111111-1111-1111-1111-111111111111',
        'cccccccc-0000-0000-0000-000000000001', 'note', 'internal',
        'ancient note', now() - interval '3 years')
on conflict (id) do nothing;

select apply_retention();

do $$
declare v record; n int;
begin
  -- Stale contact anonymised (PII stripped, row kept).
  select first_name, email into v
    from contacts where id = 'cccccccc-0000-0000-0000-000000000001';
  if v.first_name <> '[redacted]' or v.email is not null then
    raise exception 'T5a: stale contact not anonymised (name=%, email=%)', v.first_name, v.email;
  end if;

  -- Fresh contact untouched.
  select first_name into v from contacts where id = 'cccccccc-0000-0000-0000-000000000002';
  if v.first_name <> 'FreshLead' then
    raise exception 'T5b: fresh contact wrongly anonymised (name=%)', v.first_name;
  end if;

  -- Original demo contact (recent) still intact -> Acme still has Tom.
  select count(*) into n from contacts
    where id = '55555555-5555-5555-5555-555555555555' and first_name = 'Tom';
  if n <> 1 then raise exception 'T5c: recent contact Tom was wrongly swept'; end if;

  -- Stale activity hard-deleted; recent demo activity kept.
  select count(*) into n from activities where id = 'eeeeeeee-0000-0000-0000-000000000001';
  if n <> 0 then raise exception 'T5d: stale activity not deleted'; end if;
  select count(*) into n from activities where id = '88888888-8888-8888-8888-888888888888';
  if n <> 1 then raise exception 'T5e: recent demo activity wrongly deleted'; end if;

  -- Audit trail written for the sweep.
  select count(*) into n from audit_log where action like 'retention_%';
  if n < 1 then raise exception 'T5f: retention sweep wrote no audit_log rows'; end if;
end $$;

-- Idempotency: a second sweep changes nothing further (0 new anonymisations).
do $$
declare affected_total int;
begin
  select coalesce(sum(affected),0) into affected_total from apply_retention();
  if affected_total <> 0 then
    raise exception 'T5g: second retention sweep was not idempotent (% affected)', affected_total;
  end if;
end $$;
\echo '   ok'

\echo '== T6: deal stage-change trigger drives pipeline automation (W2) =='
-- Move the demo deal (currently in New Lead) to the Won stage.
do $$
declare won_stage uuid; v record; n int;
begin
  select id into won_stage from stages
    where pipeline_id = '44444444-4444-4444-4444-444444444444' and is_won limit 1;

  update deals set stage_id = won_stage
    where id = '77777777-7777-7777-7777-777777777777';

  -- Deal marked won + closed.
  select status, closed_at into v from deals
    where id = '77777777-7777-7777-7777-777777777777';
  if v.status <> 'won' or v.closed_at is null then
    raise exception 'T6a: deal not marked won/closed (status=%)', v.status;
  end if;

  -- Linked contact promoted to customer.
  select kind into v from contacts where id = '55555555-5555-5555-5555-555555555555';
  if v.kind <> 'customer' then
    raise exception 'T6b: contact not promoted to customer (kind=%)', v.kind;
  end if;

  -- The move was logged to the activity timeline.
  select count(*) into n from activities
    where deal_id = '77777777-7777-7777-7777-777777777777'
      and subject = 'Stage changed';
  if n < 1 then raise exception 'T6c: stage change not logged as activity'; end if;
end $$;

-- Moving back to an open stage reopens the deal (no recursion / status sticks).
do $$
declare lead_stage uuid; v record;
begin
  select id into lead_stage from stages
    where pipeline_id = '44444444-4444-4444-4444-444444444444' and name = 'New Lead';
  update deals set stage_id = lead_stage
    where id = '77777777-7777-7777-7777-777777777777';
  select status, closed_at into v from deals
    where id = '77777777-7777-7777-7777-777777777777';
  if v.status <> 'open' or v.closed_at is not null then
    raise exception 'T6d: deal not reopened on move back (status=%)', v.status;
  end if;
end $$;
\echo '   ok'

\echo '== T7: reconcile_billing flags silently-unpaid subscriptions (W9) =='
-- Stale: active sub whose next charge was due 3 days ago, no payment -> past_due.
insert into subscriptions (id, account_id, paypal_subscription_id, status, next_billing_at)
values ('dddddddd-0000-0000-0000-000000000001',
        '11111111-1111-1111-1111-111111111111', 'I-STALESUB001', 'active',
        now() - interval '3 days')
on conflict (id) do nothing;
update accounts set status = 'active' where id = '11111111-1111-1111-1111-111111111111';

-- Healthy: active sub billing in the future -> must stay active.
insert into accounts (id, name, slug, status)
  values ('aaaaaaaa-1111-1111-1111-111111111111', 'Healthy Co', 'healthy-co', 'active')
  on conflict (id) do nothing;
insert into subscriptions (id, account_id, paypal_subscription_id, status, next_billing_at)
values ('dddddddd-0000-0000-0000-000000000002',
        'aaaaaaaa-1111-1111-1111-111111111111', 'I-HEALTHYSUB1', 'active',
        now() + interval '20 days')
on conflict (id) do nothing;

select reconcile_billing();

do $$
declare v text; n int;
begin
  select status into v from subscriptions where id = 'dddddddd-0000-0000-0000-000000000001';
  if v <> 'past_due' then raise exception 'T7a: stale subscription not flagged (status=%)', v; end if;

  select status into v from accounts where id = '11111111-1111-1111-1111-111111111111';
  if v <> 'past_due' then raise exception 'T7b: stale account not flagged (status=%)', v; end if;

  select status into v from subscriptions where id = 'dddddddd-0000-0000-0000-000000000002';
  if v <> 'active' then raise exception 'T7c: healthy subscription wrongly flagged (status=%)', v; end if;

  select status into v from accounts where id = 'aaaaaaaa-1111-1111-1111-111111111111';
  if v <> 'active' then raise exception 'T7d: healthy account wrongly flagged (status=%)', v; end if;

  select count(*) into n from audit_log where action = 'billing_past_due';
  if n < 1 then raise exception 'T7e: reconciliation wrote no audit_log row'; end if;
end $$;

-- Idempotent: a second run flags nothing new.
do $$
declare n int;
begin
  select count(*) into n from reconcile_billing();
  if n <> 0 then raise exception 'T7f: second reconcile flagged % more (not idempotent)', n; end if;
end $$;
\echo '   ok'

\echo 'ALL ASSERTIONS PASSED'
