import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { fetchQueue, submitOverride, updateVitals } from "../services/api.js";
import { useLiveSocket } from "../hooks/useLiveSocket.js";
import QueueTable from "../components/QueueTable.jsx";
import PatientCard from "../components/PatientCard.jsx";
import PriorityBadge from "../components/PriorityBadge.jsx";
import VitalTrendChart from "../components/VitalTrendChart.jsx";

const POLL_MS = 15000; // fallback only — the WebSocket is the primary refresh trigger

export default function LiveQueue() {
  const [queue, setQueue] = useState(null);
  const [sort, setSort] = useState("priority");
  const [view, setView] = useState("table");
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);
  const [trendPoints, setTrendPoints] = useState({});
  const [toast, setToast] = useState(null);
  const inFlightRef = useRef(false);

  // Overlap guard: a full /queue scan can legitimately take several
  // seconds server-side. Without this, a slow response plus a fixed
  // timer meant the NEXT poll could fire before the previous one
  // finished, and requests would pile up indefinitely rather than ever
  // catching up — this was the root cause of a prior runaway-log
  // incident (see backend/app/services/prediction_cache.py for the
  // matching server-side fix). Skipping a tick here is always safe:
  // the WebSocket is the primary refresh trigger, this timer is a
  // fallback only.
  function refresh(currentSort = sort) {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    fetchQueue(currentSort)
      .then((data) => setQueue(data))
      .catch(() => setError("Could not reach the backend API."))
      .finally(() => {
        inFlightRef.current = false;
      });
  }

  useEffect(() => {
    refresh(sort);
    const interval = setInterval(() => refresh(sort), POLL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sort]);

  const { connected } = useLiveSocket({
    new_patient: (e) => {
      setToast({ kind: "new", text: `New patient ${e.patient_id} — ${e.priority}` });
      refresh();
    },
    override: (e) => {
      setToast({ kind: "override", text: `${e.patient_id} overridden: ${e.original_priority} → ${e.new_priority}` });
      refresh();
    },
    vitals_updated: (e) => {
      setToast({ kind: e.worsened ? "worsened" : "info", text: e.message });
      refresh();
    },
    reassessment_alert: (e) => {
      setToast({ kind: "alert", text: e.message });
    },
    retriage_breach: (e) => {
      setToast({
        kind: "breach",
        text: e.message,
        priority: e.priority,
        waited: e.waited_minutes,
        limit: e.safe_minutes,
      });
    },
  });

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 5000);
    return () => clearTimeout(t);
  }, [toast]);

  const entries = queue?.entries ?? [];

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.text}
            initial={{ opacity: 0, y: -16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.97 }}
            className={`fixed right-6 top-32 z-50 max-w-sm overflow-hidden rounded-2xl border shadow-lift ${
              toast.kind === "breach"
                ? "border-orange-400/60 bg-orange-50"
                : toast.kind === "worsened" || toast.kind === "alert"
                ? "border-red-400/40 bg-red-50"
                : "border-accent-mint/40 bg-accent-wash"
            }`}
          >
            {toast.kind === "breach" ? (
              <div className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">⚠️</span>
                  <p className="text-sm font-bold text-orange-700">Re-Triage Required</p>
                </div>
                <p className="mt-1 text-xs text-orange-600">{toast.text}</p>
                <p className="mt-1.5 text-xs font-semibold text-orange-700">
                  {toast.priority} — waited {toast.waited}m (limit {toast.limit}m)
                </p>
              </div>
            ) : (
              <div className={`px-4 py-3 text-sm ${
                toast.kind === "worsened" || toast.kind === "alert" ? "text-red-700" : "text-accent-mintInk"
              }`}>
                {toast.text}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="xl:col-span-2">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-surface-ink">Live Queue</h1>
            <p className="flex items-center gap-2 text-sm text-surface-muted">
              {entries.length} patients
              <span className={`inline-flex items-center gap-1 text-xs ${connected ? "text-accent-mintInk" : "text-surface-muted"}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-accent-mint" : "bg-slate-500"}`} />
                {connected ? "Live" : "Reconnecting…"}
              </span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <div className="flex overflow-hidden rounded-lg border border-surface-border">
              {[["priority", "Recommended"], ["cps", "CPS"], ["arrival", "Arrival"]].map(([value, label]) => (
                <button key={value} onClick={() => setSort(value)}
                  className={`px-3 py-1.5 text-xs font-medium ${sort === value ? "bg-accent-mint text-surface-ink" : "text-slate-600 hover:bg-slate-50"}`}>
                  {label}
                </button>
              ))}
            </div>
            <div className="flex overflow-hidden rounded-lg border border-surface-border">
              <button onClick={() => setView("table")}
                className={`px-3 py-1.5 text-xs font-medium ${view === "table" ? "bg-slate-100 text-surface-ink" : "text-surface-muted hover:bg-slate-50"}`}>
                Table
              </button>
              <button onClick={() => setView("cards")}
                className={`px-3 py-1.5 text-xs font-medium ${view === "cards" ? "bg-slate-100 text-surface-ink" : "text-surface-muted hover:bg-slate-50"}`}>
                Cards
              </button>
            </div>
          </div>
        </div>

        {sort !== "arrival" && (
          <div className="mb-4 rounded-lg border border-accent-mint/30 bg-accent-wash px-4 py-2 text-xs text-accent-mintInk">
            This is a recommended-order preview only. No patient has actually been reprioritized — a nurse must act via Override.
          </div>
        )}

        {error && <div className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-600">{error}</div>}

        {!error && view === "table" && (
          <QueueTable entries={entries} sort={sort} onSelect={setSelected} selectedIds={selected ? [selected.stay_id] : []} />
        )}

        {!error && view === "cards" && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {entries.map((entry) => (
              <PatientCard key={entry.stay_id} entry={entry} onClick={setSelected} selected={selected?.stay_id === entry.stay_id} />
            ))}
          </div>
        )}
      </div>

      <div className="xl:sticky xl:top-6 xl:self-start">
        {!selected && (
          <div className="panel p-6 text-sm text-surface-muted">
            Select a patient to review, override, or update vitals.
          </div>
        )}
        {selected && (
          <PatientDetailPanel
            entry={selected}
            onClose={() => setSelected(null)}
            onOverridden={refresh}
            trendPoints={trendPoints[selected.stay_id] ?? []}
            onVitalsUpdated={(point) =>
              setTrendPoints((prev) => ({
                ...prev,
                [selected.stay_id]: [...(prev[selected.stay_id] ?? []), point],
              }))
            }
          />
        )}
      </div>
    </div>
  );
}

function PatientDetailPanel({ entry, onClose, onOverridden, trendPoints, onVitalsUpdated }) {
  const [newPriority, setNewPriority] = useState(entry.priority);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const [vitals, setVitals] = useState({ heart_rate: "", resp_rate: "", sbp: "", o2_sat: "" });

  async function handleOverride() {
    if (!reason.trim()) {
      setMsg("A reason is required to record an override.");
      return;
    }
    setBusy(true);
    try {
      await submitOverride({
        stayId: entry.stay_id, originalPriority: entry.priority, newPriority, reason,
      });
      setMsg("Override recorded and logged to the audit trail.");
      onOverridden();
    } catch {
      setMsg("Could not record the override.");
    } finally {
      setBusy(false);
    }
  }

  async function handleVitalsUpdate() {
    setBusy(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(vitals).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)])
      );
      const result = await updateVitals(entry.stay_id, payload);
      onVitalsUpdated({
        label: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        ...payload,
      });
      setMsg(`Rescored: ${result.recommendation.priority} (risk ${result.recommendation.risk_score})`);
      onOverridden();
    } catch {
      setMsg("Could not update vitals.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
      className="space-y-4 panel p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-surface-ink">Stay #{entry.stay_id}</p>
          <p className="text-xs text-surface-muted">{entry.chief_complaint || "Not documented"}</p>
        </div>
        <button onClick={onClose} className="text-xs text-surface-muted hover:text-slate-600">Close ×</button>
      </div>

      <div className="flex items-center gap-2">
        <PriorityBadge priority={entry.priority} />
        {entry.overridden && <span className="text-xs text-violet-600">AI recommended {entry.recommended_priority}</span>}
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-surface-muted">Record override</h3>
        <div className="mt-2 flex gap-2">
          <select value={newPriority} onChange={(e) => setNewPriority(e.target.value)}
            className="rounded-lg border border-surface-border bg-[#FAFBFC] px-2 py-1.5 text-sm text-surface-ink">
            {["P1", "P2", "P3", "P4", "P5"].map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (required)"
            className="flex-1 rounded-lg border border-surface-border bg-[#FAFBFC] px-2 py-1.5 text-sm text-surface-ink placeholder-surface-muted" />
        </div>
        <button onClick={handleOverride} disabled={busy}
          className="mt-2 w-full rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs font-semibold text-purple-200 hover:bg-purple-500/20 disabled:opacity-50">
          Record override
        </button>
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-surface-muted">Update vitals & re-score</h3>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {[["heart_rate", "HR"], ["resp_rate", "RR"], ["sbp", "SBP"], ["o2_sat", "SpO2"]].map(([key, label]) => (
            <input key={key} value={vitals[key]} placeholder={label}
              onChange={(e) => setVitals((v) => ({ ...v, [key]: e.target.value }))}
              className="rounded-lg border border-surface-border bg-[#FAFBFC] px-2 py-1.5 text-sm text-surface-ink placeholder-surface-muted" />
          ))}
        </div>
        <button onClick={handleVitalsUpdate} disabled={busy}
          className="mt-2 w-full rounded-lg border border-accent-mint/40 bg-accent-wash px-3 py-2 text-xs font-semibold text-accent-mintInk hover:bg-accent-mint/15 disabled:opacity-50">
          Update vitals
        </button>
      </div>

      {msg && <p className="rounded-lg bg-white px-3 py-2 text-xs text-slate-600">{msg}</p>}

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-surface-muted">Vitals trend (this session)</h3>
        <div className="mt-2">
          <VitalTrendChart points={trendPoints} />
        </div>
      </div>
    </motion.div>
  );
}
