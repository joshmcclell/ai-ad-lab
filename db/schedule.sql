-- =============================================================================
-- FlowBase CRM — scheduled jobs (optional, Supabase / pg_cron)
-- Apply on a database that has the pg_cron extension available (Supabase does:
-- Dashboard → Database → Extensions → enable "pg_cron"). Safe to re-run.
--
--   psql "$DATABASE_URL" -f db/schedule.sql
--
-- This schedules the GDPR retention sweep (W7) to run in-database every night.
-- Backups (W8) cannot run here — pg_dump needs shell access — so run db/backup.sh
-- from an external scheduler (cron on a free VM, a GitHub Action, or n8n).
-- =============================================================================

create extension if not exists pg_cron;

-- Re-running should not stack duplicate jobs.
do $$
begin
  if exists (select 1 from cron.job where jobname = 'flowbase-retention') then
    perform cron.unschedule('flowbase-retention');
  end if;
  if exists (select 1 from cron.job where jobname = 'flowbase-reconcile-billing') then
    perform cron.unschedule('flowbase-reconcile-billing');
  end if;
end $$;

-- Nightly at 02:00 UTC: enforce every tenant's data_retention_policies (W7).
select cron.schedule('flowbase-retention', '0 2 * * *', $$ select apply_retention(); $$);

-- Daily at 01:00 UTC: flag silently-unpaid subscriptions as past_due (W9).
select cron.schedule('flowbase-reconcile-billing', '0 1 * * *', $$ select reconcile_billing(); $$);

-- Inspect with:   select * from cron.job;
-- History:        select * from cron.job_run_details order by start_time desc limit 20;
