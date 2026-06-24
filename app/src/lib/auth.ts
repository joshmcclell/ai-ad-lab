import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { IS_DEMO, demoUser } from "@/lib/demo";

// Resolves the signed-in user and their FlowBase users-row (role + tenant).
// RLS lets a user read their own row; a platform admin can read all rows.
export async function getCurrentUser() {
  if (IS_DEMO) {
    return {
      authUser: { id: demoUser.id, email: demoUser.email } as { id: string; email: string },
      profile: demoUser,
    };
  }
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: profile } = await supabase
    .from("users")
    .select("id, account_id, email, full_name, role, is_platform_admin")
    .eq("auth_uid", user.id)
    .maybeSingle();

  return { authUser: user, profile: profile as UserProfile | null };
}

export interface UserProfile {
  id: string;
  account_id: string | null;
  email: string;
  full_name: string | null;
  role: string;
  is_platform_admin: boolean;
}

export async function isPlatformAdmin(): Promise<boolean> {
  const current = await getCurrentUser();
  return current?.profile?.is_platform_admin === true;
}

// Guard for operator-only pages/actions. Redirects non-admins to the dashboard.
export async function requirePlatformAdmin() {
  if (!(await isPlatformAdmin())) redirect("/dashboard");
}
