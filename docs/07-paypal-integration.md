# 7. PayPal Integration — Recurring £99 Retainer

This is the money path. Goal: every client's £99/month flows **directly into
your PayPal account**, and the system auto-updates each client's payment status.

PayPal supports recurring billing natively via **Subscriptions** (Products →
Plans → Subscriptions). You create the plan **once** and reuse it for every
client. GBP is supported.

---

## A. One-time setup (do once)

### 1. PayPal Business account
- Sign up / upgrade to a **Business** account at paypal.com (free). This is the
  account that receives all payouts. Complete identity verification so you can
  withdraw to your bank.

### 2. Get API credentials
- Go to **developer.paypal.com → Dashboard → Apps & Credentials**.
- Note both **Sandbox** (for testing) and **Live** Client ID + Secret.
- Always build and test in **Sandbox** first, then flip to Live.

### 3. Create the £99/month product + plan
Easiest (no-code) route — the PayPal dashboard:
- **paypal.com → Pay & Get Paid → Subscriptions → Create plan.**
- Product: "FlowBase CRM". Plan: **£99.00 GBP / every 1 month**, no setup fee,
  no trial (or add a free trial if you want).
- Save and copy the **Plan ID** (`P-XXXXXXXXXXXX`).

Or via API (Path B / automation):
```bash
# 1) Create product
curl -s -X POST https://api-m.paypal.com/v1/catalogs/products \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"FlowBase CRM","type":"SERVICE","category":"SOFTWARE"}'

# 2) Create the £99/month plan (use product id from above)
curl -s -X POST https://api-m.paypal.com/v1/billing/plans \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "product_id":"PROD-XXXX",
    "name":"FlowBase CRM Monthly Retainer",
    "billing_cycles":[{
      "frequency":{"interval_unit":"MONTH","interval_count":1},
      "tenure_type":"REGULAR","sequence":1,"total_cycles":0,
      "pricing_scheme":{"fixed_price":{"value":"99","currency_code":"GBP"}}
    }],
    "payment_preferences":{
      "auto_bill_outstanding":true,
      "setup_fee":{"value":"0","currency_code":"GBP"},
      "payment_failure_threshold":2
    }
  }'
```
Store the returned `P-...` Plan ID in `subscriptions.paypal_plan_id` (it's the
same for every client).

### 4. Create a subscribe link/button per signup
- **No-code:** in the Subscriptions UI, generate a **shareable subscribe link**
  or a **Smart Subscription Button** and put it on your signup/onboarding page.
- **API:** create a subscription with the plan id and redirect the client to the
  returned `approve` link:
```bash
curl -s -X POST https://api-m.paypal.com/v1/billing/subscriptions \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" \
  -d '{"plan_id":"P-XXXX",
       "custom_id":"<account_id>",      // ties the payment to the tenant
       "application_context":{
         "brand_name":"FlowBase CRM",
         "return_url":"https://app.flowbasecrm.com/welcome",
         "cancel_url":"https://app.flowbasecrm.com/cancelled"}}'
```
> Put the tenant's `account_id` in `custom_id` so the webhook can match payment →
> client automatically.

### 5. Configure webhooks (auto-tracking)
- **developer.paypal.com → Apps & Credentials → your app → Add Webhook.**
- URL = your n8n/Make webhook (Path A) or Supabase Edge Function (Path B).
- Subscribe to these events:
  - `BILLING.SUBSCRIPTION.ACTIVATED`
  - `BILLING.SUBSCRIPTION.CANCELLED`
  - `BILLING.SUBSCRIPTION.SUSPENDED`
  - `BILLING.SUBSCRIPTION.PAYMENT.FAILED`
  - `PAYMENT.SALE.COMPLETED` (the monthly £99 charge)
- Copy the **Webhook ID** (needed to verify signatures).

---

## B. What happens on each event (auto-tracking)

Implemented as workflows **W5/W6** in `04-workflows-automation.md`:

| PayPal event | System action |
|--------------|---------------|
| `SUBSCRIPTION.ACTIVATED` | `subscriptions.status='active'`, `accounts.status='active'` |
| `PAYMENT.SALE.COMPLETED` | insert `payments` row; update `last_payment_at`, `current_period_end`, `next_billing_at` |
| `PAYMENT.FAILED` | `accounts.status='past_due'`; alert you + dunning email |
| `SUBSCRIPTION.SUSPENDED` | `subscriptions.status='suspended'`; `accounts.status='paused'` |
| `SUBSCRIPTION.CANCELLED` | `subscriptions.status='cancelled'`; `accounts.status='cancelled'` |

**Always verify the webhook signature** before acting, using PayPal's
`/v1/notifications/verify-webhook-signature` with your Webhook ID — this stops
spoofed "payment received" calls.

## C. Reconciliation safety net (W9)
Webhooks occasionally don't deliver. A daily job flags any subscription whose
`current_period_end` has passed without a matching payment as `past_due`, so a
silent failure can't let a non-paying client keep access.

## D. One-off invoices (when needed)
For ad-hoc charges (e.g. a custom export), use **PayPal → Invoicing → Create
invoice**, or the Invoicing API. These also fire `INVOICING.INVOICE.PAID`, which
you can log into `payments` the same way.

## E. Go-live
1. Run the whole flow in **Sandbox** (test buyer account) end-to-end.
2. Confirm a `payments` row + `accounts.status='active'` appear.
3. Switch Client ID/Secret + Plan ID + webhook to **Live**.
4. Do one real £99 subscription on yourself; confirm payout lands, then refund.

> **Fees:** PayPal charges a per-transaction fee (no monthly fee). You net
> roughly £95–96 of each £99 depending on your country's rate. This comes out of
> revenue — your fixed running cost stays £0.
