import { motion } from "framer-motion";

// PatientTriage.ai — Triage Stay Table
//
// Uses the acuity color palette already reserved in tailwind.config.js
// (triage.critical/urgent/moderate/low/nonurgent) so acuity 1-5 reads
// the same way everywhere in the app. Untriaged stays get a distinct
// slate badge rather than falling through to a default color — "unknown"
// must never visually look like "clear", per the platform's safety principle.

const ACUITY_STYLE = {
  1: { label: "1 · Critical", className: "bg-red-50 text-red-700 border-red-200" },
  2: { label: "2 · Urgent", className: "bg-orange-50 text-orange-700 border-orange-200" },
  3: { label: "3 · Moderate", className: "bg-yellow-50 text-yellow-700 border-yellow-200" },
  4: { label: "4 · Low", className: "bg-green-50 text-green-700 border-green-200" },
  5: { label: "5 · Non-urgent", className: "bg-blue-50 text-blue-700 border-blue-200" },
};
const UNTRIAGED_STYLE = { label: "Untriaged", className: "bg-slate-100 text-slate-600 border-surface-border" };

function AcuityBadge({ acuity }) {
  const style = acuity == null ? UNTRIAGED_STYLE : ACUITY_STYLE[acuity] ?? UNTRIAGED_STYLE;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${style.className}`}>
      {style.label}
    </span>
  );
}

function fmtVital(value, unit = "") {
  if (value === null || value === undefined) {
    return <span className="text-surface-muted">—</span>;
  }
  const rounded = typeof value === "number" ? Math.round(value * 10) / 10 : value;
  return (
    <span>
      {rounded}
      {unit}
    </span>
  );
}

export default function TriageStayTable({ stays, loading }) {
  if (loading) {
    return (
      <div className="panel p-6">
        <p className="text-sm text-surface-muted">Loading triage stays…</p>
      </div>
    );
  }

  if (!stays || stays.length === 0) {
    return (
      <div className="panel p-6">
        <p className="text-sm text-surface-muted">No triage stays match the current filter.</p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="overflow-hidden panel"
    >
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Acuity</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Chief complaint</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Temp</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">HR</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">RR</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">O2</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">SBP/DBP</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Arrival</th>
              <th className="px-4 py-3 text-left font-semibold text-slate-600">Model flag</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {stays.map((stay) => (
              <tr key={stay.stay_id} className="hover:bg-slate-50">
                <td className="whitespace-nowrap px-4 py-3">
                  <AcuityBadge acuity={stay.acuity} />
                </td>
                <td className="max-w-xs truncate px-4 py-3 text-slate-600" title={stay.chief_complaint || ""}>
                  {stay.chief_complaint || <span className="text-surface-muted">Not documented</span>}
                  {stay.missing_history_flag && (
                    <span className="ml-2 text-xs text-amber-600" title="Incomplete history documented at triage">
                      ⚠ incomplete history
                    </span>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">{fmtVital(stay.temperature, "°F")}</td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">{fmtVital(stay.heart_rate)}</td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">{fmtVital(stay.resp_rate)}</td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">{fmtVital(stay.o2_sat, "%")}</td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                  {stay.sbp != null && stay.dbp != null ? (
                    `${Math.round(stay.sbp)}/${Math.round(stay.dbp)}`
                  ) : (
                    <span className="text-surface-muted">—</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-slate-600">{stay.arrival_transport ?? "—"}</td>
                <td className="whitespace-nowrap px-4 py-3">
                  {stay.predicted_high_acuity === null || stay.predicted_high_acuity === undefined ? (
                    <span className="text-xs text-surface-muted">not scored</span>
                  ) : stay.predicted_high_acuity ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700">
                      ▲ high risk · {(stay.predicted_probability * 100).toFixed(0)}%
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                      lower risk · {(stay.predicted_probability * 100).toFixed(0)}%
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
