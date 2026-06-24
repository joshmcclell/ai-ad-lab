import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { contactName, formatDate } from "@/lib/format";
import { addActivity } from "../../actions";
import type { Activity, Contact } from "@/lib/types";

export default async function ContactDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const supabase = createClient();

  const [{ data: contact }, { data: activityRows }] = await Promise.all([
    supabase.from("contacts").select("*").eq("id", params.id).maybeSingle(),
    supabase
      .from("activities")
      .select("*")
      .eq("contact_id", params.id)
      .order("occurred_at", { ascending: false })
      .limit(100),
  ]);

  if (!contact) notFound();
  const c = contact as Contact;
  const activities = (activityRows ?? []) as Activity[];

  return (
    <div className="max-w-3xl">
      <Link href="/contacts" className="text-sm text-brand">
        ← Contacts
      </Link>

      <h1 className="mt-2 text-2xl font-semibold">{contactName(c)}</h1>
      <dl className="mt-4 grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-white p-5 text-sm">
        <Field label="Email" value={c.email} />
        <Field label="Phone" value={c.phone} />
        <Field label="Company" value={c.company} />
        <Field label="Job title" value={c.job_title} />
        <Field label="Source" value={c.source} />
        <Field label="Kind" value={c.kind} />
        <Field
          label="Marketing consent"
          value={c.consent_marketing ? `Yes (${formatDate(c.consent_at)})` : "No"}
        />
      </dl>

      <h2 className="mt-8 text-lg font-semibold">Activity log</h2>

      {/* Add a note (central communication log) */}
      <form action={addActivity} className="mt-3 flex gap-2">
        <input type="hidden" name="contact_id" value={c.id} />
        <input type="hidden" name="account_id" value={c.account_id} />
        <input
          name="body"
          placeholder="Log a note, call, or email…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand"
        />
        <button className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90">
          Add
        </button>
      </form>

      <ul className="mt-4 space-y-3">
        {activities.length === 0 ? (
          <li className="text-sm text-slate-400">No activity yet.</li>
        ) : (
          activities.map((a) => (
            <li key={a.id} className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {a.type}
                </span>
                <span className="text-xs text-slate-400">{formatDate(a.occurred_at)}</span>
              </div>
              {a.subject && <p className="mt-1 text-sm font-medium">{a.subject}</p>}
              {a.body && <p className="mt-1 text-sm text-slate-700">{a.body}</p>}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 capitalize">{value || "—"}</dd>
    </div>
  );
}
