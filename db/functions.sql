-- =============================================================================
-- FlowBase CRM — server-side functions
-- Apply AFTER schema.sql (and before/after policies.sql):
--   psql "$DATABASE_URL" -f db/functions.sql
-- =============================================================================

-- provision_account(): the "add a client" routine (docs/06 Step 7, docs/09).
-- Atomically stands up a new tenant: account + default pipeline & stages +
-- default GDPR retention policies + the owner user. Returns the new account_id.
--
-- SECURITY DEFINER so it can write across the RLS-protected tenant tables when
-- called from a trusted context (the PayPal webhook via service role, an
-- operator action, or a provisioning script). search_path is pinned.
--
-- Atomic by nature: a function body is one transaction, so a failure at any step
-- (e.g. a duplicate owner email) rolls back the whole tenant — no half-created
-- accounts.
create or replace function provision_account(
  p_name           text,
  p_owner_email    citext,
  p_owner_name     text default null,
  p_owner_auth_uid uuid default null
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_account_id  uuid;
  v_pipeline_id uuid;
begin
  if p_name is null or length(trim(p_name)) = 0 then
    raise exception 'account name is required';
  end if;
  if p_owner_email is null then
    raise exception 'owner email is required';
  end if;

  insert into accounts (name, status)
    values (p_name, 'active')
    returning id into v_account_id;

  insert into pipelines (account_id, name, is_default)
    values (v_account_id, 'Sales Pipeline', true)
    returning id into v_pipeline_id;

  insert into stages (account_id, pipeline_id, name, position, probability, is_won, is_lost)
  values
    (v_account_id, v_pipeline_id, 'New Lead',      0,  10, false, false),
    (v_account_id, v_pipeline_id, 'Contacted',     1,  25, false, false),
    (v_account_id, v_pipeline_id, 'Qualified',     2,  50, false, false),
    (v_account_id, v_pipeline_id, 'Proposal Sent', 3,  70, false, false),
    (v_account_id, v_pipeline_id, 'Won',           4, 100, true,  false),
    (v_account_id, v_pipeline_id, 'Lost',          5,   0, false, true);

  insert into data_retention_policies (account_id, entity, retain_days, action)
  values
    (v_account_id, 'contact',  1095, 'anonymize'),   -- 3 years post inactivity
    (v_account_id, 'activity',  730, 'delete');       -- 2 years

  insert into users (account_id, auth_uid, email, full_name, role)
    values (v_account_id, p_owner_auth_uid, p_owner_email, p_owner_name, 'owner');

  return v_account_id;
end;
$$;

-- apply_retention(): the GDPR retention sweep (workflow W7, docs/10).
-- Walks every active row in data_retention_policies and enforces it:
--   contact  + anonymize -> strip PII, keep the row for aggregates
--   contact  + delete    -> soft-delete (deleted_at), hard-deleted later by grace
--   activity + delete    -> hard-delete old communication-log rows
--   activity + anonymize -> blank the subject/body, keep the row
-- Records a per-policy summary in audit_log and returns what it did. Idempotent:
-- already-processed rows fall outside the where-clauses on the next run.
-- Reference time is last activity (falling back to created_at) so retention is
-- measured from inactivity, not creation.
create or replace function apply_retention()
returns table(entity text, action text, affected integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  pol     record;
  n       integer;
  cutoff  timestamptz;
begin
  for pol in select * from data_retention_policies where is_active loop
    n := 0;
    cutoff := now() - make_interval(days => pol.retain_days);

    if pol.entity = 'contact' and pol.action = 'anonymize' then
      with done as (
        update contacts c
           set first_name = '[redacted]', last_name = null, email = null,
               phone = null, company = null, job_title = null,
               consent_marketing = false, updated_at = now()
         where c.account_id = pol.account_id
           and c.deleted_at is null
           and c.first_name is distinct from '[redacted]'
           and coalesce(c.last_activity_at, c.created_at) < cutoff
        returning 1)
      select count(*) into n from done;

    elsif pol.entity = 'contact' and pol.action = 'delete' then
      with done as (
        update contacts c set deleted_at = now()
         where c.account_id = pol.account_id
           and c.deleted_at is null
           and coalesce(c.last_activity_at, c.created_at) < cutoff
        returning 1)
      select count(*) into n from done;

    elsif pol.entity = 'activity' and pol.action = 'delete' then
      with done as (
        delete from activities a
         where a.account_id = pol.account_id and a.occurred_at < cutoff
        returning 1)
      select count(*) into n from done;

    elsif pol.entity = 'activity' and pol.action = 'anonymize' then
      with done as (
        update activities a set subject = null, body = '[redacted]'
         where a.account_id = pol.account_id
           and a.occurred_at < cutoff
           and a.body is distinct from '[redacted]'
        returning 1)
      select count(*) into n from done;
    end if;

    if n > 0 then
      insert into audit_log (account_id, action, entity, changes)
      values (pol.account_id, 'retention_' || pol.action, pol.entity,
              jsonb_build_object('affected', n, 'retain_days', pol.retain_days));
    end if;

    entity := pol.entity; action := pol.action; affected := n;
    return next;
  end loop;
end;
$$;
