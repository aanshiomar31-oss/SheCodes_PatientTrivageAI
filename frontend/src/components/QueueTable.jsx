import PriorityBadge from "./PriorityBadge.jsx";

/**
 * QueueTable — the columns requested: Priority, Clinical Priority Score,
 * Wait Time, Confidence, Status. `sort` only affects DISPLAY order; the
 * backend's canonical queue order (arrival) is unaffected by choosing a
 * CPS preview — see backend/app/api/routes/queue.py's list_queue()
 * docstring for the enforcement of "never automatically change queue
 * order."
 */
export default function QueueTable({ entries, sort, onSelect, selectedIds = [] }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="panel p-6 text-sm text-surface-muted">
        No patients currently in queue.
      </div>
    );
  }

  return (
    <div className="overflow-hidden panel">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-surface-border/50 text-sm">
          <thead className="bg-white">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Patient</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Priority</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">
                CPS {sort === "cps" && <span className="text-accent-mintInk">(sorted)</span>}
              </th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Wait Time</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Confidence</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border/60">
            {entries.map((entry) => (
              <tr
                key={entry.stay_id}
                onClick={() => onSelect?.(entry)}
                className={`cursor-pointer transition hover:bg-slate-50 ${
                  selectedIds.includes(entry.stay_id) ? "bg-accent-wash" : ""
                }`}
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-surface-ink">#{entry.stay_id}</p>
                  <p className="max-w-xs truncate text-xs text-surface-muted">
                    {entry.chief_complaint || "Not documented"}
                  </p>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <PriorityBadge priority={entry.priority} compact />
                    {entry.overridden && (
                      <span className="text-xs text-violet-600" title={`AI recommended ${entry.recommended_priority}`}>
                        overridden
                      </span>
                    )}
                    {entry.escalated && <span className="text-xs text-red-500">⚠</span>}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 rounded-full bg-slate-100">
                      <div
                        className="h-1.5 rounded-full bg-sky-400"
                        style={{ width: `${entry.cps * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-600">{(entry.cps * 100).toFixed(0)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-600">{Math.round(entry.waited_minutes)}m</td>
                <td className="px-4 py-3">
                  <span
                    className={
                      entry.confidence >= 0.75
                        ? "text-accent-mintInk"
                        : entry.confidence >= 0.6
                          ? "text-yellow-400"
                          : "text-red-500"
                    }
                  >
                    {(entry.confidence * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-xs uppercase tracking-wide text-surface-muted">{entry.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
