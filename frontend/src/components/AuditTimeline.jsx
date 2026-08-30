import { useState } from "react";

export default function AuditTimeline({ logs }) {
  const [filterText, setFilterText] = useState("");
  const [filterAction, setFilterAction] = useState("");

  const filteredLogs = (logs || []).filter((log) => {
    const matchText =
      log.user.toLowerCase().includes(filterText.toLowerCase()) ||
      log.device.toLowerCase().includes(filterText.toLowerCase()) ||
      log.patient.toLowerCase().includes(filterText.toLowerCase());
    const matchAction = filterAction ? log.action === filterAction : true;
    return matchText && matchAction;
  });

  const uniqueActions = Array.from(new Set((logs || []).map((l) => l.action)));

  return (
    <div className="panel p-5 space-y-4">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h3 className="label">Live Security Audit Logs</h3>
          <p className="text-xs text-surface-muted mt-1">Real-time trace of critical database and security events.</p>
        </div>

        {/* Filter controls */}
        <div className="flex gap-2 flex-wrap">
          <input
            type="text"
            placeholder="Search User/Device..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="rounded-lg border border-surface-border bg-accent-wash px-2.5 py-1 text-xs text-surface-ink placeholder-surface-muted focus:outline-none focus:border-accent-mint"
          />
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="rounded-lg border border-surface-border bg-accent-wash px-2.5 py-1 text-xs text-surface-ink focus:outline-none focus:border-accent-mint"
          >
            <option value="">All Actions</option>
            {uniqueActions.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-y-auto max-h-[350px] space-y-3 pr-1">
        {filteredLogs.length === 0 ? (
          <p className="text-xs text-surface-muted text-center py-6">No matching logs found.</p>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex justify-between items-start p-3 bg-surface-bg/10 border border-surface-border rounded-xl hover:bg-surface-bg/30 transition text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">{log.user}</span>
                  <span className="text-[10px] text-surface-muted">({log.device})</span>
                </div>
                <p className="text-surface-muted">
                  Action: <span className="text-white font-medium">{log.action}</span>
                </p>
                {log.patient !== "N/A" && (
                  <p className="text-[10px] text-accent-mint font-semibold">Target: {log.patient}</p>
                )}
              </div>
              <div className="text-right space-y-1 shrink-0">
                <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-bold bg-accent-wash text-accent-mint">
                  {log.status}
                </span>
                <p className="text-[9px] text-surface-muted">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
