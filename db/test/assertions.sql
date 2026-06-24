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

\echo 'ALL ASSERTIONS PASSED'
