-- =============================================================================
-- FlowBase CRM — Row-Level Security policies (enable when using Supabase Auth)
-- =============================================================================
-- Model: every tenant table carries account_id. A signed-in user may only see
-- rows for THEIR account. The platform super-admin (is_platform_admin = true)
-- bypasses isolation. We resolve the caller's account_id from the users table
-- via their auth uid (Supabase sets auth.uid()).
--
-- Apply AFTER schema.sql:  psql "$DATABASE_URL" -f db/policies.sql
-- On Supabase, auth.uid() is provided automatically. For a plain self-hosted
-- Postgres you can set it per request with:  SET app.current_user_id = '<uuid>';
-- and replace auth.uid() below with current_setting('app.current_user_id')::uuid.
-- =============================================================================

-- Portability shim: on Supabase the `auth` schema and auth.uid() already exist,
-- so this block does nothing. On a plain self-hosted Postgres it creates a
-- stand-in auth.uid() that reads the per-session GUC `app.current_user_id`, so you
-- can drive RLS yourself with:  SET app.current_user_id = '<users.auth_uid>';
do $$
begin
  if not exists (select 1 from pg_namespace where nspname = 'auth') then
    create schema auth;
    execute $f$
      create function auth.uid() returns uuid language sql stable as
      $g$ select nullif(current_setting('app.current_user_id', true), '')::uuid $g$;
    $f$;
    -- Let application roles resolve their identity (Supabase grants this itself).
    grant usage on schema auth to public;
    grant execute on function auth.uid() to public;
  end if;
end $$;

-- Helpers resolve the caller's identity from `users`. They MUST be
-- SECURITY DEFINER: the tenant_isolation policy on `users` itself calls these
-- helpers, so without bypassing RLS here the policy would recurse infinitely.
-- search_path is pinned for safety (a SECURITY DEFINER best practice).

-- account_id of the current caller (null for super-admin)
create or replace function current_account_id() returns uuid
language sql stable security definer set search_path = public as $$
  select account_id from users where auth_uid = auth.uid() limit 1
$$;

create or replace function is_super_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select coalesce(
    (select is_platform_admin from users where auth_uid = auth.uid() limit 1),
  false)
$$;

-- Apply the same tenant policy to every tenant-scoped table.
do $$
declare t text;
begin
  foreach t in array array[
    'accounts','subscriptions','payments','users','contacts','tags',
    'contact_tags','custom_fields','custom_field_values','pipelines','stages',
    'deals','activities','tasks','calendar_events','audit_log',
    'data_retention_policies'
  ] loop
    execute format('alter table %I enable row level security;', t);

    -- contact_tags has no account_id directly; skip the generic policy for it.
    if t <> 'contact_tags' and t <> 'accounts' then
      execute format($f$
        drop policy if exists tenant_isolation on %1$I;
        create policy tenant_isolation on %1$I
          using (is_super_admin() or account_id = current_account_id())
          with check (is_super_admin() or account_id = current_account_id());
      $f$, t);
    end if;
  end loop;

  -- accounts: a user sees only their own account row (super-admin sees all)
  execute $f$
    drop policy if exists tenant_isolation on accounts;
    create policy tenant_isolation on accounts
      using (is_super_admin() or id = current_account_id())
      with check (is_super_admin() or id = current_account_id());
  $f$;

  -- contact_tags: isolate via the parent contact's account
  execute $f$
    drop policy if exists tenant_isolation on contact_tags;
    create policy tenant_isolation on contact_tags
      using (is_super_admin() or exists (
        select 1 from contacts c
        where c.id = contact_tags.contact_id
          and c.account_id = current_account_id()))
      with check (is_super_admin() or exists (
        select 1 from contacts c
        where c.id = contact_tags.contact_id
          and c.account_id = current_account_id()));
  $f$;
end $$;
