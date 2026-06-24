"use server";

import { revalidatePath } from "next/cache";
import { isPlatformAdmin } from "@/lib/auth";
import { createAdminClient } from "@/lib/supabase/admin";
import { IS_DEMO } from "@/lib/demo";

export interface ProvisionResult {
  ok: boolean;
  message: string;
  accountId?: string;
}

// Operator action: manually stand up a new client tenant. Calls the
// provision_account() DB function via the service-role client (cross-tenant
// write). Guarded so only platform admins can run it.
export async function provisionClient(
  _prev: ProvisionResult | null,
  formData: FormData
): Promise<ProvisionResult> {
  if (!(await isPlatformAdmin())) {
    return { ok: false, message: "Not authorised." };
  }

  const name = String(formData.get("name") ?? "").trim();
  const email = String(formData.get("owner_email") ?? "").trim();
  const ownerName = String(formData.get("owner_name") ?? "").trim() || null;

  if (!name || !email) {
    return { ok: false, message: "Client name and owner email are required." };
  }
  if (IS_DEMO) {
    return { ok: true, message: `(Demo) Would provision "${name}". Connect Supabase to make it real.` };
  }

  const supabase = createAdminClient();
  const { data, error } = await supabase.rpc("provision_account", {
    p_name: name,
    p_owner_email: email,
    p_owner_name: ownerName,
  });

  if (error) {
    return { ok: false, message: error.message };
  }

  revalidatePath("/admin");
  return {
    ok: true,
    message: `Provisioned "${name}".`,
    accountId: data as string,
  };
}
