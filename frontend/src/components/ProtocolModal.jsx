import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const COLOR_MAP = {
  red: {
    overlay: "bg-red-900/60",
    card: "border-red-400 bg-white",
    header: "bg-red-600",
    badge: "bg-red-100 text-red-700",
    check: "border-red-300 text-red-500 focus:ring-red-400/40",
    timer: "text-red-600",
    btnClose: "border-red-200 text-red-600 hover:bg-red-50",
  },
  orange: {
    overlay: "bg-orange-900/60",
    card: "border-amber-400 bg-white",
    header: "bg-amber-500",
    badge: "bg-amber-100 text-amber-700",
    check: "border-amber-300 text-amber-500 focus:ring-amber-400/40",
    timer: "text-amber-600",
    btnClose: "border-amber-200 text-amber-600 hover:bg-amber-50",
  },
};

/**
 * ProtocolModal — full-screen takeover with nurse checklist for time-critical
 * protocols (Stroke, STEMI, Anaphylaxis, Airway Crisis).
 *
 * Props:
 *   protocols  — array of protocol objects from TriageResponse.triggered_protocols
 *   patientId  — string like "ED0204"
 *   onClose    — callback (called after nurse works through checklist or dismisses)
 */
export default function ProtocolModal({ protocols, patientId, onClose }) {
  const [activeIdx, setActiveIdx] = useState(0);
  const [checked, setChecked] = useState({});

  if (!protocols?.length) return null;

  const protocol = protocols[activeIdx];
  const c = COLOR_MAP[protocol.color] ?? COLOR_MAP.red;
  const checkedCount = Object.values(checked[protocol.code] ?? {}).filter(Boolean).length;
  const totalItems = protocol.checklist.length;

  function toggle(code, id) {
    setChecked((prev) => ({
      ...prev,
      [code]: { ...(prev[code] ?? {}), [id]: !(prev[code]?.[id]) },
    }));
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className={`fixed inset-0 z-50 flex items-center justify-center p-4 ${c.overlay} backdrop-blur-sm`}
        role="dialog"
        aria-modal="true"
        aria-label={`${protocol.title} protocol`}
      >
        <motion.div
          initial={{ scale: 0.93, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 10 }}
          transition={{ type: "spring", stiffness: 320, damping: 28 }}
          className={`w-full max-w-lg overflow-hidden rounded-3xl border-2 shadow-lift ${c.card}`}
        >
          {/* Header */}
          <div className={`${c.header} px-6 py-5 text-white`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{protocol.icon}</span>
                <div>
                  <p className="text-xl font-bold">{protocol.title}</p>
                  <p className="text-sm font-medium text-white/80">
                    Patient {patientId} — Door-to-intervention target:{" "}
                    {protocol.urgency_minutes === 0
                      ? "IMMEDIATE"
                      : `${protocol.urgency_minutes} min`}
                  </p>
                </div>
              </div>
              {protocols.length > 1 && (
                <span className="rounded-full bg-white/20 px-2.5 py-1 text-xs font-semibold">
                  {activeIdx + 1}/{protocols.length}
                </span>
              )}
            </div>

            {/* Progress bar */}
            <div className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-white/25">
              <motion.div
                className="h-full rounded-full bg-white"
                animate={{ width: `${(checkedCount / totalItems) * 100}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <p className="mt-1 text-right text-xs text-white/70">
              {checkedCount}/{totalItems} steps completed
            </p>
          </div>

          {/* Rationale */}
          <div className="border-b border-surface-border bg-slate-50 px-6 py-3">
            <p className="text-xs text-surface-muted italic">{protocol.rationale}</p>
          </div>

          {/* Checklist */}
          <div className="max-h-72 overflow-y-auto px-6 py-4">
            <div className="space-y-3">
              {protocol.checklist.map((item) => {
                const done = checked[protocol.code]?.[item.id];
                return (
                  <motion.label
                    key={item.id}
                    htmlFor={`proto-${protocol.code}-${item.id}`}
                    whileTap={{ scale: 0.98 }}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                      done
                        ? "border-green-200 bg-green-50"
                        : "border-surface-border hover:border-surface-muted"
                    }`}
                  >
                    <input
                      id={`proto-${protocol.code}-${item.id}`}
                      type="checkbox"
                      checked={done ?? false}
                      onChange={() => toggle(protocol.code, item.id)}
                      className={`mt-0.5 shrink-0 rounded ${c.check}`}
                    />
                    <div className="flex-1">
                      <p className={`text-sm font-medium ${done ? "text-green-700 line-through" : "text-surface-ink"}`}>
                        {item.text}
                      </p>
                      {item.time_target_minutes !== null && item.time_target_minutes !== undefined && (
                        <p className={`mt-0.5 text-xs font-semibold ${c.timer}`}>
                          ⏱ Target: within {item.time_target_minutes} min
                        </p>
                      )}
                    </div>
                  </motion.label>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between gap-3 border-t border-surface-border px-6 py-4">
            {/* Protocol tabs if multiple */}
            {protocols.length > 1 ? (
              <div className="flex gap-2">
                {protocols.map((p, i) => (
                  <button
                    key={p.code}
                    onClick={() => setActiveIdx(i)}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                      i === activeIdx
                        ? "bg-surface-ink text-white"
                        : "border border-surface-border text-surface-muted hover:bg-slate-50"
                    }`}
                  >
                    {p.icon} {p.title.split(" ")[0]}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-surface-muted">
                All actions are audit logged automatically.
              </p>
            )}

            <button
              id="protocol-modal-close-btn"
              onClick={onClose}
              className={`rounded-xl border px-5 py-2.5 text-sm font-semibold transition ${c.btnClose} focus:outline-none focus:ring-2 focus:ring-current/30`}
            >
              {checkedCount === totalItems ? "✓ Done" : "Dismiss"}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
