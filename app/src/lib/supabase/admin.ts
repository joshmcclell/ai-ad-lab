import { createClient } from "@supabase/supabase-js";

// Service-role client. BYPASSES Row-Level Security — use ONLY in trusted
// server contexts that legitimately need cross-tenant writes, e.g. the PayPal
// webhook updating any client's subscription/payment status. Never import this
// into a client component.
export function createAdminClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { persistSession: false, autoRefreshToken: false } }
  );
}
