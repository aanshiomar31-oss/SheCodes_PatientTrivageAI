import { useEffect, useState } from "react";
import { fetchQueue, fetchTriageStay } from "../services/api.js";
import RadarComparison from "../components/RadarComparison.jsx";
import PriorityBadge from "../components/PriorityBadge.jsx";
import ConfidenceGauge from "../components/ConfidenceGauge.jsx";

const MAX_SELECTION = 4;
const VITAL_ROWS = [
  ["heart_rate", "Heart rate", "bpm"], ["resp_rate", "Resp. rate", "/min"],
  ["sbp", "Systolic BP", "mmHg"], ["dbp", "Diastolic BP", "mmHg"],
  ["o2_sat", "O2 saturation", "%"], ["temperature", "Temperature", ""],
  ["pain", "Pain", "/10"],
];

export default function PatientComparison() {
  const [queueEntries, setQueueEntries] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [details, setDetails] = useState({}); // stay_id -> full triage_stay record

  useEffect(() => {
    fetchQueue("arrival").then((data) => setQueueEntries(data.entries)).catch(() => {});
  }, []);

  useEffect(() => {
    selectedIds.forEach((id) => {
      if (!details[id]) {
        fetchTriageStay(id)
          .then((data) => setDetails((prev) => ({ ...prev, [id]: data })))
          .catch(() => {});
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIds]);

  function toggle(id) {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= MAX_SELECTION) return prev;
      return [...prev, id];
    });
  }

  const selectedEntries = queueEntries.filter((e) => selectedIds.includes(e.stay_id));
  const radarData = selectedIds
    .map((id) => details[id])
    .filter(Boolean)
    .map((d) => ({
      stay_id: d.stay_id,
      heart_rate: d.heart_rate,
      resp_rate: d.resp_rate,
      sbp: d.sbp,
      o2_sat: d.o2_sat,
      temperature: d.temperature,
      pain: d.pain,
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-ink">Patient Comparison</h1>
        <p className="text-sm text-surface-muted">Select up to {MAX_SELECTION} patients to compare side by side.</p>
      </div>

      <div className="panel p-4">
        <div className="flex flex-wrap gap-2">
          {queueEntries.map((e) => (
            <button
              key={e.stay_id}
              onClick={() => toggle(e.stay_id)}
              disabled={!selectedIds.includes(e.stay_id) && selectedIds.length >= MAX_SELECTION}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
                selectedIds.includes(e.stay_id)
                  ? "border-accent-mint bg-accent-wash text-accent-mintInk"
                  : "border-surface-border text-surface-muted hover:bg-slate-50"
              }`}
            >
              #{e.stay_id} · {e.priority}
            </button>
          ))}
        </div>
      </div>

      {selectedEntries.length === 0 && (
        <p className="text-sm text-surface-muted">No patients selected yet.</p>
      )}

      {selectedEntries.length > 0 && (
        <>
          <div className="panel p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Vitals radar (normalized)</h2>
            <RadarComparison patients={radarData} />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {selectedEntries.map((e) => (
              <div key={e.stay_id} className="panel p-4">
                <p className="text-sm font-semibold text-surface-ink">Stay #{e.stay_id}</p>
                <p className="mt-0.5 text-xs text-surface-muted">{e.chief_complaint || "Not documented"}</p>
                <div className="mt-3"><PriorityBadge priority={e.priority} /></div>
                <div className="mt-3 flex justify-center"><ConfidenceGauge confidence={e.confidence} size={110} /></div>
                <p className="mt-2 text-center text-xs text-surface-muted">Risk {e.risk_score}/100</p>
              </div>
            ))}
          </div>

          <div className="overflow-hidden panel">
            <table className="min-w-full divide-y divide-surface-border/50 text-sm">
              <thead className="bg-white">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold text-slate-600">Vital</th>
                  {selectedEntries.map((e) => (
                    <th key={e.stay_id} className="px-4 py-3 text-left font-semibold text-slate-600">#{e.stay_id}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {VITAL_ROWS.map(([key, label, unit]) => (
                  <tr key={key}>
                    <td className="px-4 py-3 text-surface-muted">{label}</td>
                    {selectedIds.map((id) => {
                      const d = details[id];
                      const value = d ? d[key] : undefined;
                      return (
                        <td key={id} className="px-4 py-3 text-surface-ink">
                          {value === undefined || value === null ? (
                            <span className="text-slate-600">—</span>
                          ) : (
                            `${value}${unit}`
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">AI recommendation summary</h2>
            <ul className="mt-3 space-y-2">
              {selectedEntries.map((e) => (
                <li key={e.stay_id} className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm">
                  <span className="text-slate-600">
                    #{e.stay_id} — {e.uncertainty_reason || "No uncertainty flagged"}
                  </span>
                  <PriorityBadge priority={e.priority} compact />
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
