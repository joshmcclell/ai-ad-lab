"use client";

import { useFormState, useFormStatus } from "react-dom";
import { provisionClient, type ProvisionResult } from "./actions";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
    >
      {pending ? "Provisioning…" : "Provision client"}
    </button>
  );
}

export function ProvisionForm() {
  const [state, formAction] = useFormState<ProvisionResult | null, FormData>(
    provisionClient,
    null
  );

  return (
    <form action={formAction} className="space-y-3 rounded-xl border border-slate-200 bg-white p-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <input
          name="name"
          placeholder="Client business name"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand"
        />
        <input
          name="owner_email"
          type="email"
          placeholder="Owner email"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand"
        />
        <input
          name="owner_name"
          placeholder="Owner name (optional)"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand"
        />
      </div>
      <div className="flex items-center gap-3">
        <SubmitButton />
        {state && (
          <span className={`text-sm ${state.ok ? "text-green-600" : "text-red-600"}`}>
            {state.message}
          </span>
        )}
      </div>
    </form>
  );
}
