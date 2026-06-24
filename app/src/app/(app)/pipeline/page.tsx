import { createClient } from "@/lib/supabase/server";
import { formatMoney } from "@/lib/format";
import { moveDeal } from "../actions";
import type { Deal, Stage } from "@/lib/types";

// Visual pipeline board: stages as columns, deals as cards. Moving a deal uses a
// lightweight <select> server action (no client-side drag dependency needed).
export default async function PipelinePage() {
  const supabase = createClient();

  const [{ data: stageRows }, { data: dealRows }] = await Promise.all([
    supabase.from("stages").select("*").order("position", { ascending: true }),
    supabase.from("deals").select("*").eq("status", "open"),
  ]);

  const stages = (stageRows ?? []) as Stage[];
  const deals = (dealRows ?? []) as Deal[];
  const byStage = (stageId: string) => deals.filter((d) => d.stage_id === stageId);

  return (
    <div>
      <h1 className="text-2xl font-semibold">Pipeline</h1>

      <div className="mt-6 flex gap-4 overflow-x-auto pb-4">
        {stages.map((stage) => {
          const cards = byStage(stage.id);
          const total = cards.reduce((s, d) => s + d.value_pennies, 0);
          return (
            <div key={stage.id} className="w-72 flex-shrink-0">
              <div className="mb-2 flex items-center justify-between px-1">
                <span className="text-sm font-semibold">{stage.name}</span>
                <span className="text-xs text-slate-500">{formatMoney(total)}</span>
              </div>
              <div className="space-y-2 rounded-xl bg-white p-2 ring-1 ring-slate-200">
                {cards.length === 0 ? (
                  <p className="px-2 py-4 text-center text-xs text-slate-400">Empty</p>
                ) : (
                  cards.map((d) => (
                    <div key={d.id} className="rounded-lg border border-slate-200 p-3">
                      <p className="text-sm font-medium">{d.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        {formatMoney(d.value_pennies, d.currency)}
                      </p>
                      <form action={moveDeal} className="mt-2">
                        <input type="hidden" name="deal_id" value={d.id} />
                        <select
                          name="stage_id"
                          defaultValue={d.stage_id}
                          className="w-full rounded border border-slate-200 px-2 py-1 text-xs"
                        >
                          {stages.map((s) => (
                            <option key={s.id} value={s.id}>
                              Move to: {s.name}
                            </option>
                          ))}
                        </select>
                        <button className="mt-1 w-full rounded bg-surface px-2 py-1 text-xs text-slate-600 hover:bg-slate-100">
                          Update stage
                        </button>
                      </form>
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
