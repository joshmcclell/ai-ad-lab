import { createBrowserClient } from "@supabase/ssr";

// Browser Supabase client (anon key). Used by client components for auth and
// any client-side reads — still RLS-scoped to the signed-in tenant.
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );
}
