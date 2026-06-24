// Single data-access layer for the app's pages. In demo mode it returns the
// in-memory sample data (no backend); otherwise it queries Supabase under RLS.
// Keeping the branch here means the page components stay identical either way.

import { createClient } from "@/lib/supabase/server";
import {
  IS_DEMO, demoAccounts, demoActivities, demoContacts, demoConversion,
  demoDeals, demoPipelineValue, demoStages, demoTasks,
} from "@/lib/demo";
import type {
  Account, Activity, Contact, ConversionRow, Deal, PipelineValueRow, Stage, Task,
} from "@/lib/types";

export async function loadDashboard(): Promise<{
  leadCount: number;
  conversion: ConversionRow | null;
  pipeline: PipelineValueRow[];
}> {
  if (IS_DEMO) {
    return {
      leadCount: demoContacts.filter((c) => c.kind === "lead").length,
      conversion: demoConversion,
      pipeline: demoPipelineValue,
    };
  }
  const supabase = createClient();
  const [{ data: pipeline }, { data: conversion }, { count }] = await Promise.all([
    supabase.from("v_pipeline_value").select("*"),
    supabase.from("v_conversion").select("*").maybeSingle(),
    supabase.from("contacts").select("*", { count: "exact", head: true }).eq("kind", "lead"),
  ]);
  return {
    leadCount: count ?? 0,
    conversion: (conversion ?? null) as ConversionRow | null,
    pipeline: (pipeline ?? []) as PipelineValueRow[],
  };
}

export async function loadContacts(): Promise<Contact[]> {
  if (IS_DEMO) return demoContacts;
  const supabase = createClient();
  const { data } = await supabase
    .from("contacts").select("*").is("deleted_at", null)
    .order("created_at", { ascending: false }).limit(200);
  return (data ?? []) as Contact[];
}

export async function loadContact(
  id: string
): Promise<{ contact: Contact | null; activities: Activity[] }> {
  if (IS_DEMO) {
    return {
      contact: demoContacts.find((c) => c.id === id) ?? null,
      activities: demoActivities[id] ?? [],
    };
  }
  const supabase = createClient();
  const [{ data: contact }, { data: activities }] = await Promise.all([
    supabase.from("contacts").select("*").eq("id", id).maybeSingle(),
    supabase.from("activities").select("*").eq("contact_id", id)
      .order("occurred_at", { ascending: false }).limit(100),
  ]);
  return {
    contact: (contact ?? null) as Contact | null,
    activities: (activities ?? []) as Activity[],
  };
}

export async function loadPipeline(): Promise<{ stages: Stage[]; deals: Deal[] }> {
  if (IS_DEMO) return { stages: demoStages, deals: demoDeals };
  const supabase = createClient();
  const [{ data: stages }, { data: deals }] = await Promise.all([
    supabase.from("stages").select("*").order("position", { ascending: true }),
    supabase.from("deals").select("*").eq("status", "open"),
  ]);
  return { stages: (stages ?? []) as Stage[], deals: (deals ?? []) as Deal[] };
}

export async function loadTasks(): Promise<Task[]> {
  if (IS_DEMO) return demoTasks;
  const supabase = createClient();
  const { data } = await supabase
    .from("tasks").select("*").eq("status", "open")
    .order("due_at", { ascending: true }).limit(200);
  return (data ?? []) as Task[];
}

export async function loadAccounts(): Promise<
  (Account & { created_at: string; subscriptions: { status: string; last_payment_at: string | null }[] | null })[]
> {
  if (IS_DEMO) return demoAccounts;
  const supabase = createClient();
  const { data } = await supabase
    .from("accounts")
    .select("id, name, status, plan_price_pennies, plan_currency, created_at, subscriptions(status, last_payment_at)")
    .order("created_at", { ascending: false });
  return (data ?? []) as unknown as (Account & {
    created_at: string;
    subscriptions: { status: string; last_payment_at: string | null }[] | null;
  })[];
}
