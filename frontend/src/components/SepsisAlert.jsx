import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

/**
 * Enhanced SepsisAlert — Premium clinical glassmorphism alert banner.
 */
export default function SepsisAlert({ result, onAcknowledge }) {
  const [acknowledged, setAcknowledged] = useState(false);

  if (!result?.sepsis_alert) return null;
  if (acknowledged) return null;

  const isHigh = result.sepsis_risk_level === "high";

  function handleAck() {
    setAcknowledged(true);
    onAcknowledge?.({ stay_id: result.patient_id, risk_level: result.sepsis_risk_level });
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -16, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -10, scale: 0.95 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className={`relative overflow-hidden rounded-2xl border backdrop-blur-md p-6 shadow-lg ${
          isHigh
            ? "border-red-500/30 bg-white/80 shadow-red-500/5"
            : "border-amber-500/30 bg-white/80 shadow-amber-500/5"
        }`}
      >
        {/* Pulsing Left Strip */}
        <motion.div
          animate={{ opacity: [1, 0.5, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className={`absolute left-0 top-0 h-full w-1.5 ${
            isHigh ? "bg-red-500" : "bg-amber-500"
          }`}
        />

        <div>
          {/* Header Info */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className={`relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
                isHigh ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600"
              }`}>
                <span className="text-xl">🦠</span>
                <span className={`absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5 rounded-full ${
                  isHigh ? "bg-red-500" : "bg-amber-500"
                } ring-2 ring-white`}>
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
                </span>
              </div>
              <div>
                <h3 className={`text-base font-bold tracking-tight ${isHigh ? "text-red-900" : "text-amber-900"}`}>
                  {isHigh ? "SEPSIS PROTOCOL ACTIVE" : "Sepsis Alert / Watch"}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Based on current physiological assessment criteria
                </p>
              </div>
            </div>

            <span className={`rounded-lg px-2.5 py-1 text-2xs font-extrabold uppercase tracking-wider ${
              isHigh ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
            }`}>
              qSOFA Score: {result.sepsis_qsofa}/3
            </span>
          </div>

          {/* Clinical Message */}
          <div className={`mt-4 rounded-xl p-3.5 text-xs leading-relaxed ${
            isHigh ? "bg-red-50/50 text-red-800" : "bg-amber-50/50 text-amber-800"
          }`}>
            {result.sepsis_message}
          </div>

          {/* Criteria Pills Breakdown */}
          {result.sepsis_criteria?.length > 0 && (
            <div className="mt-4">
              <p className="text-2xs font-bold uppercase tracking-wider text-slate-400 mb-2">Triggered Indicators</p>
              <div className="flex flex-wrap gap-1.5">
                {result.sepsis_criteria.map((c, i) => (
                  <span
                    key={i}
                    className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-2xs font-semibold ${
                      isHigh
                        ? "bg-red-500/5 text-red-700 border border-red-500/10"
                        : "bg-amber-500/5 text-amber-700 border border-amber-500/10"
                    }`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${isHigh ? "bg-red-500" : "bg-amber-500"}`} />
                    {c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 1-Hour Sepsis Bundle Checklist */}
          {isHigh && (
            <div className="mt-5 rounded-xl border border-red-100 bg-slate-50/50 p-4">
              <p className="text-2xs font-bold uppercase tracking-wider text-red-600 mb-3">
                1-Hour Management Bundle Checklist
              </p>
              <div className="space-y-2">
                {[
                  "Blood cultures drawn × 2 (prior to antimicrobials)",
                  "Serum lactate measurement ordered stat",
                  "Broad-spectrum IV antibiotics prepared & initiated",
                  "Rapid fluid resuscitation started (30mL/kg crystalloid if hypotensive or lactate ≥4)",
                  "Prepare vasopressors if map remains < 65 mmHg",
                ].map((item, i) => (
                  <label
                    key={i}
                    className="flex cursor-pointer items-start gap-3 text-xs text-slate-700 hover:text-slate-900 transition"
                  >
                    <input
                      type="checkbox"
                      id={`sepsis-bundle-${i}`}
                      className="mt-0.5 rounded border-slate-300 text-red-600 focus:ring-red-500/30"
                    />
                    <span>{item}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Acknowledge Button Bar */}
          <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4">
            <p className="text-2xs font-medium text-slate-400">
              Actions and acknowledgement are automatically logged in the audit trail.
            </p>
            <button
              id="sepsis-acknowledge-btn"
              onClick={handleAck}
              className={`rounded-xl px-5 py-2.5 text-xs font-bold text-white transition-all duration-200 shadow-md ${
                isHigh
                  ? "bg-red-600 hover:bg-red-700 hover:shadow-red-600/10 active:scale-95"
                  : "bg-amber-500 hover:bg-amber-600 hover:shadow-amber-500/10 active:scale-95"
              }`}
            >
              Acknowledge Alert
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
