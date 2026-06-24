# 9. Client Onboarding Process

Designed to take **under 30 minutes of your time per client**, most of it
automated. The aim: payment and provisioning happen without you, and you only
do a short personal welcome.

## The flow (signup → live in a day)

```
Prospect books a call (Cal.com)
        │
        ▼
You demo + send subscribe link  ──►  Client subscribes via PayPal (£99/mo)
        │                                     │
        │                      PayPal webhook (W5) fires
        ▼                                     ▼
                          System auto-provisions the tenant:
                          • accounts row (status=active)
                          • default pipeline + stages
                          • retention policies
                          • client's first user + invite email
                                              │
                                              ▼
                          Welcome email with login + booking link
                                              │
                                              ▼
                You import their contacts (CSV) + 15-min walkthrough
```

## Step-by-step

1. **Discovery call** (Cal.com booking). 15–20 min: confirm it's a fit, show the
   board + dashboard.
2. **Send the subscribe link** (`07-paypal-integration.md`). The `custom_id` =
   their new `account_id`.
3. **Payment → auto-provision.** PayPal webhook W5 creates/activates the tenant
   and emails their login. You do nothing here.
4. **Data import.** Ask for a CSV of existing contacts; import into `contacts`
   (set `source='Imported'`, capture consent basis). Path A: NocoDB CSV import.
   Path B: `\copy` / Supabase import.
5. **15-minute walkthrough** (recorded once, reuse the video) covering: add a
   lead, move a deal, log a note, read the dashboard.
6. **Handover checklist** (send as email):
   - [ ] Login works, password set
   - [ ] Pipeline stages match their sales process (tweak if needed)
   - [ ] Lead form embedded on their website
   - [ ] Calendar connected
   - [ ] Team members invited with correct roles
   - [ ] GDPR consent + retention settings confirmed

## Templates to prepare once (reuse forever)
- Welcome email (auto-sent by W5).
- "Send me your contacts" CSV request email + a CSV template.
- 15-min walkthrough video (Loom free).
- Handover checklist email.
- 1-page "getting started" PDF.

## Offboarding (cancellation)
On `SUBSCRIPTION.CANCELLED` (W6): set `accounts.status='cancelled'`, email a
**data export** (requirement #8), keep data for a short grace window per your
retention policy, then anonymise/delete. Log every step to `audit_log`.
