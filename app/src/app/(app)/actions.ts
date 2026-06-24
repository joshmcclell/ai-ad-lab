"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { IS_DEMO } from "@/lib/demo";

export async function signOut() {
  if (IS_DEMO) redirect("/dashboard");
  const supabase = createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

// Log a note/activity against a contact (central communication log).
export async function addActivity(formData: FormData) {
  const contactId = String(formData.get("contact_id"));
  const accountId = String(formData.get("account_id"));
  const body = String(formData.get("body") ?? "").trim();
  if (!body) return;
  if (IS_DEMO) {
    revalidatePath(`/contacts/${contactId}`);
    return;
  }

  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // account_id is required by the schema and enforced by RLS; we pass the
  // contact's account_id (the user can only see their own tenant anyway).
  await supabase.from("activities").insert({
    account_id: accountId,
    contact_id: contactId,
    user_id: user?.id ?? null,
    type: "note",
    direction: "internal",
    body,
  });

  revalidatePath(`/contacts/${contactId}`);
}

// Move a deal to another stage (drag-free: a simple select on the board).
export async function moveDeal(formData: FormData) {
  const dealId = String(formData.get("deal_id"));
  const stageId = String(formData.get("stage_id"));
  if (IS_DEMO) {
    revalidatePath("/pipeline");
    return;
  }

  const supabase = createClient();
  await supabase.from("deals").update({ stage_id: stageId }).eq("id", dealId);

  revalidatePath("/pipeline");
}

// Toggle a task between open and done.
export async function completeTask(formData: FormData) {
  const taskId = String(formData.get("task_id"));
  if (IS_DEMO) {
    revalidatePath("/tasks");
    return;
  }
  const supabase = createClient();
  await supabase
    .from("tasks")
    .update({ status: "done", completed_at: new Date().toISOString() })
    .eq("id", taskId);
  revalidatePath("/tasks");
}
