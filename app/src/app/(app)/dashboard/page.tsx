import { StatCard } from "@/components/StatCard";
import { formatMoney } from "@/lib/format";
import { loadDashboard } from "@/lib/data";

// Real-time dashboard built on the reporting views in db/schema.sql.
export default async function DashboardPage() {
  const { leadCount, conversion: conv, pipeline: rows } = await loadDashboard();

  const pipelineValue = rows.reduce((sum, r) => sum + (r.open_value_pennies ?? 0), 0);
  const openDeals = rows.reduce((sum, r) => sum + (r.open_deals ?? 0), 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Open leads" value={String(leadCount ?? 0)} />
        <StatCard
          label="Conversion rate"
          value={conv?.win_rate_pct != null ? `${conv.win_rate_pct}%` : "—"}
          hint={conv ? `${conv.won} won / ${conv.closed} closed` : undefined}
        />
        <StatCard label="Pipeline value" value={formatMoney(pipelineValue)} />
        <StatCard label="Open deals" value={String(openDeals)} />
      </div>

      <h2 className="mt-10 text-lg font-semibold">Pipeline by stage</h2>
      <div className="mt-3 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-surface text-left text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Stage</th>
              <th className="px-4 py-2 font-medium">Open deals</th>
              <th className="px-4 py-2 font-medium">Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-3 text-slate-400" colSpan={3}>
                  No deals yet.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.stage_id} className="border-t border-slate-100">
                  <td className="px-4 py-2">{r.stage_name}</td>
                  <td className="px-4 py-2">{r.open_deals}</td>
                  <td className="px-4 py-2">{formatMoney(r.open_value_pennies)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
