import { createClient } from "@/lib/supabase/server";
import { formatDate } from "@/lib/format";
import { completeTask } from "../actions";
import type { Task } from "@/lib/types";

export default async function TasksPage() {
  const supabase = createClient();
  const { data } = await supabase
    .from("tasks")
    .select("*")
    .eq("status", "open")
    .order("due_at", { ascending: true })
    .limit(200);

  const tasks = (data ?? []) as Task[];
  const now = Date.now();

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold">Tasks</h1>

      <ul className="mt-6 space-y-2">
        {tasks.length === 0 ? (
          <li className="text-sm text-slate-400">No open tasks. 🎉</li>
        ) : (
          tasks.map((t) => {
            const overdue = t.due_at != null && new Date(t.due_at).getTime() < now;
            return (
              <li
                key={t.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3"
              >
                <div>
                  <p className="text-sm font-medium">{t.title}</p>
                  <p className={`text-xs ${overdue ? "text-red-600" : "text-slate-500"}`}>
                    Due {formatDate(t.due_at)}
                    {overdue ? " · overdue" : ""}
                  </p>
                </div>
                <form action={completeTask}>
                  <input type="hidden" name="task_id" value={t.id} />
                  <button className="rounded-lg border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-surface">
                    Done
                  </button>
                </form>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}
