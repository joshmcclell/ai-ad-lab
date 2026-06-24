-- =============================================================================
-- FlowBase CRM — seed data (one demo tenant + default pipeline + sample records)
-- Run AFTER schema.sql:  psql "$DATABASE_URL" -f db/seed.sql
-- Safe to re-run: uses fixed UUIDs + ON CONFLICT.
-- =============================================================================

-- Platform super-admin (you). account_id NULL = sees all tenants.
insert into users (id, account_id, email, full_name, role, is_platform_admin)
values ('00000000-0000-0000-0000-0000000000aa', null,
        'owner@flowbasecrm.com', 'FlowBase Operator', 'owner', true)
on conflict (email) do nothing;

-- Demo tenant
insert into accounts (id, name, slug, status, trial_ends_at)
values ('11111111-1111-1111-1111-111111111111', 'Acme Plumbing Ltd', 'acme-plumbing',
        'trialing', now() + interval '14 days')
on conflict (id) do nothing;

-- Tenant subscription (PayPal ids filled in by webhook on real signup)
insert into subscriptions (id, account_id, status)
values ('22222222-2222-2222-2222-222222222222',
        '11111111-1111-1111-1111-111111111111', 'approval_pending')
on conflict (id) do nothing;

-- Tenant user
insert into users (id, account_id, email, full_name, role)
values ('33333333-3333-3333-3333-333333333333',
        '11111111-1111-1111-1111-111111111111',
        'jane@acmeplumbing.co.uk', 'Jane Acme', 'admin')
on conflict (email) do nothing;

-- Default pipeline + stages
insert into pipelines (id, account_id, name, is_default)
values ('44444444-4444-4444-4444-444444444444',
        '11111111-1111-1111-1111-111111111111', 'Sales Pipeline', true)
on conflict (id) do nothing;

insert into stages (account_id, pipeline_id, name, position, probability, is_won, is_lost) values
 ('11111111-1111-1111-1111-111111111111','44444444-4444-4444-4444-444444444444','New Lead',     0, 10,false,false),
 ('11111111-1111-1111-1111-111111111111','44444444-4444-4444-4444-444444444444','Contacted',    1, 25,false,false),
 ('11111111-1111-1111-1111-111111111111','44444444-4444-4444-4444-444444444444','Qualified',    2, 50,false,false),
 ('11111111-1111-1111-1111-111111111111','44444444-4444-4444-4444-444444444444','Proposal Sent',3, 70,false,false),
 ('11111111-1111-1111-1111-111111111111','44444444-4444-4444-4444-444444444444','Won',          4,100,true, false),
 ('11111111-1111-1111-1111-111111111111','44444444-4444-4444-4444-444444444444','Lost',         5,  0,false,true )
on conflict (pipeline_id, name) do nothing;

-- Default GDPR retention policies for the tenant
insert into data_retention_policies (account_id, entity, retain_days, action) values
 ('11111111-1111-1111-1111-111111111111','contact',  1095, 'anonymize'),   -- 3 years post inactivity
 ('11111111-1111-1111-1111-111111111111','activity',  730, 'delete')        -- 2 years
on conflict (account_id, entity) do nothing;

-- Sample contact + tag + deal + activity
insert into contacts (id, account_id, kind, first_name, last_name, email, phone, company, source,
                      consent_marketing, consent_source, consent_at, lawful_basis)
values ('55555555-5555-5555-5555-555555555555',
        '11111111-1111-1111-1111-111111111111','lead','Tom','Baker',
        'tom@example.co.uk','+44 7700 900000','Baker & Sons','Website form',
        true,'Website opt-in checkbox', now(), 'consent')
on conflict (id) do nothing;

insert into tags (id, account_id, name, color)
values ('66666666-6666-6666-6666-666666666666',
        '11111111-1111-1111-1111-111111111111','Hot Lead','#dc2626')
on conflict (id) do nothing;

insert into contact_tags (contact_id, tag_id)
values ('55555555-5555-5555-5555-555555555555','66666666-6666-6666-6666-666666666666')
on conflict do nothing;

insert into deals (id, account_id, pipeline_id,
                   stage_id, contact_id, title, value_pennies)
select '77777777-7777-7777-7777-777777777777',
       '11111111-1111-1111-1111-111111111111',
       '44444444-4444-4444-4444-444444444444',
       s.id, '55555555-5555-5555-5555-555555555555',
       'Bathroom refit quote', 250000
from stages s
where s.pipeline_id = '44444444-4444-4444-4444-444444444444' and s.name = 'New Lead'
on conflict (id) do nothing;

insert into activities (id, account_id, contact_id, deal_id, type, direction, subject, body)
values ('88888888-8888-8888-8888-888888888888',
        '11111111-1111-1111-1111-111111111111',
        '55555555-5555-5555-5555-555555555555',
        '77777777-7777-7777-7777-777777777777',
        'note','internal','Initial enquiry','Came in via website contact form. Wants a quote.')
on conflict (id) do nothing;
