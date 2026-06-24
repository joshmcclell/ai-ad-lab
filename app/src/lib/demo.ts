// Demo mode: lets the app render fully with no Supabase backend and no login.
// Enabled when NEXT_PUBLIC_DEMO=1, or automatically when no Supabase URL is set
// (so a fresh `npm run dev` just works). All data below is in-memory sample data.

import type {
  Account, Activity, Contact, ConversionRow, Deal, PipelineValueRow, Stage, Task,
} from "./types";
import type { UserProfile } from "./auth";

export const IS_DEMO =
  process.env.NEXT_PUBLIC_DEMO === "1" || !process.env.NEXT_PUBLIC_SUPABASE_URL;

export const demoUser: UserProfile = {
  id: "demo-user",
  account_id: "demo-account",
  email: "you@flowbasecrm.com",
  full_name: "Demo Operator",
  role: "owner",
  is_platform_admin: true,
};

export const demoStages: Stage[] = [
  { id: "s1", account_id: "demo-account", pipeline_id: "p1", name: "New Lead", position: 0, probability: 10, is_won: false, is_lost: false },
  { id: "s2", account_id: "demo-account", pipeline_id: "p1", name: "Contacted", position: 1, probability: 25, is_won: false, is_lost: false },
  { id: "s3", account_id: "demo-account", pipeline_id: "p1", name: "Qualified", position: 2, probability: 50, is_won: false, is_lost: false },
  { id: "s4", account_id: "demo-account", pipeline_id: "p1", name: "Proposal Sent", position: 3, probability: 70, is_won: false, is_lost: false },
  { id: "s5", account_id: "demo-account", pipeline_id: "p1", name: "Won", position: 4, probability: 100, is_won: true, is_lost: false },
  { id: "s6", account_id: "demo-account", pipeline_id: "p1", name: "Lost", position: 5, probability: 0, is_won: false, is_lost: true },
];

export const demoContacts: Contact[] = [
  c("c1", "lead", "Tom", "Baker", "tom@bakerandsons.co.uk", "Baker & Sons", "Website form", true),
  c("c2", "contact", "Priya", "Shah", "priya@shahdesign.co.uk", "Shah Design", "Referral", true),
  c("c3", "customer", "Liam", "O'Connor", "liam@oconnorbuild.ie", "O'Connor Build", "Google Ads", false),
  c("c4", "lead", "Sara", "Webb", "sara@webbaccounting.co.uk", "Webb Accounting", "LinkedIn", true),
  c("c5", "contact", "Marcus", "Lin", "marcus@linfitness.com", "Lin Fitness", "Cold call", false),
];

function c(
  id: string, kind: Contact["kind"], first: string, last: string,
  email: string, company: string, source: string, consent: boolean
): Contact {
  return {
    id, account_id: "demo-account", kind, first_name: first, last_name: last,
    email, phone: "+44 7700 900000", company, job_title: "Owner", source,
    owner_user_id: "demo-user", consent_marketing: consent,
    consent_at: consent ? "2026-01-12T10:00:00Z" : null,
    last_activity_at: "2026-06-18T09:30:00Z", created_at: "2026-01-12T10:00:00Z",
  };
}

export const demoDeals: Deal[] = [
  d("d1", "s1", "c1", "Bathroom refit quote", 250000),
  d("d2", "s2", "c2", "Brand refresh package", 480000),
  d("d3", "s3", "c4", "Year-end accounts retainer", 180000),
  d("d4", "s4", "c5", "Gym fit-out CRM rollout", 990000),
  d("d5", "s2", "c1", "Maintenance contract", 120000),
];

function d(id: string, stage_id: string, contact_id: string, title: string, value: number): Deal {
  return {
    id, account_id: "demo-account", pipeline_id: "p1", stage_id, contact_id,
    title, value_pennies: value, currency: "GBP", status: "open",
    expected_close_date: "2026-07-31", created_at: "2026-06-01T10:00:00Z",
  };
}

export const demoTasks: Task[] = [
  t("t1", "Follow up with Tom Baker", "2026-06-20T09:00:00Z"),
  t("t2", "Send proposal to Lin Fitness", "2026-06-25T12:00:00Z"),
  t("t3", "Call Sara Webb re: accounts", "2026-06-28T15:00:00Z"),
];

function t(id: string, title: string, due_at: string): Task {
  return {
    id, account_id: "demo-account", contact_id: null, deal_id: null,
    assigned_user_id: "demo-user", title, description: null, due_at,
    status: "open", completed_at: null,
  };
}

export const demoActivities: Record<string, Activity[]> = {
  c1: [
    a("a1", "c1", "note", "internal", "Initial enquiry", "Came in via website contact form. Wants a quote."),
    a("a2", "c1", "call", "outbound", "Intro call", "Discussed scope, sending a quote this week."),
  ],
};

function a(
  id: string, contact_id: string, type: Activity["type"],
  direction: Activity["direction"], subject: string, body: string
): Activity {
  return {
    id, account_id: "demo-account", contact_id, deal_id: null, user_id: "demo-user",
    type, direction, subject, body, occurred_at: "2026-06-18T09:30:00Z",
  };
}

export const demoPipelineValue: PipelineValueRow[] = demoStages
  .filter((s) => !s.is_won && !s.is_lost)
  .map((s) => {
    const deals = demoDeals.filter((dl) => dl.stage_id === s.id);
    return {
      account_id: "demo-account", pipeline_id: "p1", stage_id: s.id,
      stage_name: s.name, open_deals: deals.length,
      open_value_pennies: deals.reduce((sum, dl) => sum + dl.value_pennies, 0),
    };
  });

export const demoConversion: ConversionRow = {
  account_id: "demo-account", won: 7, lost: 3, closed: 10, win_rate_pct: 70,
};

export const demoAccounts: (Account & {
  created_at: string;
  subscriptions: { status: string; last_payment_at: string | null }[];
})[] = [
  acct("demo-account", "Acme Plumbing Ltd", "active", "active", "2026-06-01T00:00:00Z"),
  acct("a2", "Shah Design", "active", "active", "2026-05-18T00:00:00Z"),
  acct("a3", "Webb Accounting", "past_due", "past_due", "2026-04-02T00:00:00Z"),
  acct("a4", "Lin Fitness", "trialing", "approval_pending", null),
];

function acct(
  id: string, name: string, status: Account["status"],
  subStatus: string, lastPaid: string | null
): Account & { created_at: string; subscriptions: { status: string; last_payment_at: string | null }[] } {
  return {
    id, name, status, plan_price_pennies: 9900, plan_currency: "GBP",
    created_at: "2026-06-01T00:00:00Z",
    subscriptions: [{ status: subStatus, last_payment_at: lastPaid }],
  };
}
