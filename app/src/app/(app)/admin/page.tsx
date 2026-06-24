import { requirePlatformAdmin } from "@/lib/auth";
import { formatMoney, formatDate } from "@/lib/format";
import { loadAccounts } from "@/lib/data";
import { ProvisionForm } from "./ProvisionForm";

// Operator console: provision new client tenants and see all accounts with
// their billing status. Platform-admin only; reads across every tenant.
export default async function AdminPage() {
  await requirePlatformAdmin();

  const accounts = await loadAccounts();

  const mrr = accounts
    .filter((a) => a.status === "active")
    .reduce((sum, a) => sum + a.plan_price_pennies, 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold">Operator console</h1>
      <p className="mt-1 text-sm text-slate-500">
        {accounts.length} client{accounts.length === 1 ? "" : "s"} ·{" "}
        {formatMoney(mrr)} MRR (active)
      </p>

      <h2 className="mt-6 text-lg font-semibold">Add a client</h2>
      <div className="mt-3">
        <ProvisionForm />
      </div>

      <h2 className="mt-8 text-lg font-semibold">All clients</h2>
      <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-surface text-left text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Client</th>
              <th className="px-4 py-2 font-medium">Account status</th>
              <th className="px-4 py-2 font-medium">Subscription</th>
              <th className="px-4 py-2 font-medium">Last payment</th>
              <th className="px-4 py-2 font-medium">Plan</th>
            </tr>
          </thead>
          <tbody>
            {accounts.length === 0 ? (
              <tr>
                <td className="px-4 py-3 text-slate-400" colSpan={5}>
                  No clients yet — provision your first above.
                </td>
              </tr>
            ) : (
              accounts.map((a) => {
                const sub = a.subscriptions?.[0];
                return (
                  <tr key={a.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-medium">{a.name}</td>
                    <td className="px-4 py-2">
                      <StatusBadge status={a.status} />
                    </td>
                    <td className="px-4 py-2">{sub?.status ?? "—"}</td>
                    <td className="px-4 py-2">{formatDate(sub?.last_payment_at ?? null)}</td>
                    <td className="px-4 py-2">
                      {formatMoney(a.plan_price_pennies, a.plan_currency)}/mo
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone =
    status === "active"
      ? "bg-green-100 text-green-700"
      : status === "past_due"
        ? "bg-amber-100 text-amber-700"
        : status === "cancelled"
          ? "bg-red-100 text-red-700"
          : "bg-slate-100 text-slate-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${tone}`}>
      {status.replace("_", " ")}
    </span>
  );
}
