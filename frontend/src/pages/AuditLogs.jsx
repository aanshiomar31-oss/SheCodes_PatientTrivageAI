import { useEffect, useMemo, useState } from "react";
import { fetchAudit } from "../services/api.js";

const EVENT_LABELS = {
  triage_recommendation: "AI recommendation",
  recommendation_overridden: "Nurse override",
  vitals_updated: "Vitals updated",
};

const EVENT_COLORS = {
  triage_recommendation: "text-accent-mintInk bg-accent-wash border-accent-mint/30",
  recommendation_overridden: "text-violet-600 bg-purple-500/10 border-purple-500/30",
  vitals_updated: "text-orange-300 bg-orange-500/10 border-orange-500/30",
};

function toCsv(entries) {
  const header = ["timestamp", "patient_id", "event_type", "actor", "details"];
  const rows = entries.map((e) => [
    e.created_at, e.patient_id, e.event_type, e.actor,
    JSON.stringify(e.details ?? {}).replace(/"/g, '""'),
  ]);
  return [header, ...rows].map((row) => row.map((cell) => `"${cell}"`).join(",")).join("\n");
}

function describeDetails(entry) {
  const d = entry.details;
  if (!d) return "—";
  if (entry.event_type === "recommendation_overridden") {
    return `${d.original_priority} → ${d.new_priority}: ${d.reason}`;
  }
  if (entry.event_type === "vitals_updated") {
    const changed = Object.entries(d.new ?? {})
      .filter(([k, v]) => v !== null && d.previous?.[k] !== v)
      .map(([k, v]) => `${k}: ${v}`);
    return changed.length ? changed.join(", ") : "Vitals recorded";
  }
  if (entry.event_type === "triage_recommendation") {
    const rec = d.recommendation ?? {};
    return `${rec.priority ?? "?"} · risk ${rec.risk_score ?? "?"} · confidence ${
      rec.confidence != null ? (rec.confidence * 100).toFixed(0) + "%" : "?"
    }`;
  }
  return JSON.stringify(d);
}

export default function AuditLogs() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [patientFilter, setPatientFilter] = useState("");
  const [eventFilter, setEventFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    fetchAudit({ limit: 500 })
      .then((data) => setEntries(data.entries))
      .catch(() => setError("Could not reach the backend API."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      if (patientFilter && !e.patient_id.toLowerCase().includes(patientFilter.trim().toLowerCase())) return false;
      if (eventFilter && e.event_type !== eventFilter) return false;
      return true;
    });
  }, [entries, patientFilter, eventFilter]);

  function handleExport() {
    const csv = toCsv(filtered);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `patienttriage_audit_${new Date().toISOString().slice(0, 19)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-surface-ink">Audit Logs</h1>
          <p className="text-sm text-surface-muted">Every AI recommendation, override, and vitals update — chronological, append-only.</p>
        </div>
        <button onClick={handleExport} disabled={filtered.length === 0}
          className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-surface-ink hover:bg-slate-50 disabled:opacity-40">
          Export CSV
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          value={patientFilter}
          onChange={(e) => setPatientFilter(e.target.value)}
          placeholder="Search patient ID (e.g. ED0204)"
          className="input mt-0 w-64"
        />
        <select
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
          className="rounded-lg border border-surface-border bg-[#FAFBFC] px-3 py-2 text-sm text-surface-ink"
        >
          <option value="">All event types</option>
          {Object.entries(EVENT_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {error && <div className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-600">{error}</div>}
      {loading && <p className="text-sm text-surface-muted">Loading…</p>}

      {!loading && !error && (
        <div className="overflow-hidden panel">
          <table className="min-w-full divide-y divide-surface-border/50 text-sm">
            <thead className="bg-white">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Time</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Patient</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Action</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Actor</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/60">
              {filtered.map((e) => (
                <tr key={e.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-3 text-surface-muted">
                    {new Date(e.created_at).toLocaleString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-surface-ink">{e.patient_id}</td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${EVENT_COLORS[e.event_type] ?? "border-surface-border text-slate-600"}`}>
                      {EVENT_LABELS[e.event_type] ?? e.event_type}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-surface-muted">{e.actor}</td>
                  <td className="px-4 py-3 text-slate-600">{describeDetails(e)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="px-4 py-6 text-center text-sm text-surface-muted">No audit entries match the current filter.</p>
          )}
        </div>
      )}
    </div>
  );
}
