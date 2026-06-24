// Domain types mirroring db/schema.sql. Kept hand-written (small surface) rather
// than generated, so the app has no build-time dependency on the live DB.

export type AccountStatus =
  | "trialing" | "active" | "past_due" | "paused" | "cancelled";
export type ContactKind = "lead" | "contact" | "customer";
export type DealStatus = "open" | "won" | "lost";
export type TaskStatus = "open" | "done" | "cancelled";
export type ActivityType = "email" | "call" | "note" | "meeting" | "sms" | "task_log";
export type ActivityDir = "inbound" | "outbound" | "internal";
export type UserRole = "owner" | "admin" | "manager" | "agent" | "viewer";

export interface Account {
  id: string;
  name: string;
  status: AccountStatus;
  plan_price_pennies: number;
  plan_currency: string;
}

export interface Contact {
  id: string;
  account_id: string;
  kind: ContactKind;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  company: string | null;
  job_title: string | null;
  source: string | null;
  owner_user_id: string | null;
  consent_marketing: boolean;
  consent_at: string | null;
  last_activity_at: string | null;
  created_at: string;
}

export interface Stage {
  id: string;
  account_id: string;
  pipeline_id: string;
  name: string;
  position: number;
  probability: number;
  is_won: boolean;
  is_lost: boolean;
}

export interface Deal {
  id: string;
  account_id: string;
  pipeline_id: string;
  stage_id: string;
  contact_id: string | null;
  title: string;
  value_pennies: number;
  currency: string;
  status: DealStatus;
  expected_close_date: string | null;
  created_at: string;
}

export interface Activity {
  id: string;
  account_id: string;
  contact_id: string | null;
  deal_id: string | null;
  user_id: string | null;
  type: ActivityType;
  direction: ActivityDir;
  subject: string | null;
  body: string | null;
  occurred_at: string;
}

export interface Task {
  id: string;
  account_id: string;
  contact_id: string | null;
  deal_id: string | null;
  assigned_user_id: string | null;
  title: string;
  description: string | null;
  due_at: string | null;
  status: TaskStatus;
  completed_at: string | null;
}

// Shape of the v_pipeline_value reporting view.
export interface PipelineValueRow {
  account_id: string;
  pipeline_id: string;
  stage_id: string;
  stage_name: string;
  open_deals: number;
  open_value_pennies: number;
}

// Shape of the v_conversion reporting view.
export interface ConversionRow {
  account_id: string;
  won: number;
  lost: number;
  closed: number;
  win_rate_pct: number | null;
}
