import { motion } from "framer-motion";
import PriorityBadge from "./PriorityBadge.jsx";
import ConfidenceGauge from "./ConfidenceGauge.jsx";

export default function AIConfidenceCard({ patient }) {
  if (!patient) {
    return (
      <div className="panel p-6 flex flex-col items-center justify-center text-center h-full">
        <p className="text-sm text-surface-muted">Select a patient from the active list to inspect AI recommendation parameters.</p>
      </div>
    );
  }

  const {
    recommended_priority = "P3",
    risk_score = 45,
    confidence = 0.85,
    uncertainty_reason = null,
    top_features = ["High Heart Rate", "Missing SpO2"],
    escalated = false,
  } = patient;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="panel p-6 space-y-4"
    >
      <div className="flex justify-between items-center border-b border-surface-border pb-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-surface-muted">AI Clinical Assessment</h3>
          <p className="text-xs text-surface-muted mt-0.5">Stay ID: #{patient.stay_id}</p>
        </div>
        <PriorityBadge priority={recommended_priority} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Gauge & Main Score */}
        <div className="flex flex-col items-center justify-center border-r border-surface-border md:pr-6">
          <ConfidenceGauge confidence={confidence} size={130} />
          <p className="text-xs text-surface-muted mt-2">Ensemble Certainty</p>
          <div className="mt-4 text-center">
            <span className="text-3xl font-extrabold text-surface-ink">{risk_score}</span>
            <span className="text-xs text-surface-muted">/100 Risk Score</span>
          </div>
        </div>

        {/* Factors & Warnings */}
        <div className="space-y-4">
          <div>
            <h4 className="text-xs font-bold uppercase text-accent-mintInk mb-2">Key Urgency Factors</h4>
            {top_features.length > 0 ? (
              <ul className="space-y-1.5 text-xs text-surface-ink">
                {top_features.map((feature, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <span className="text-accent-mint">•</span>
                    {feature}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-surface-muted">No major physiological alerts detected.</p>
            )}
          </div>

          {uncertainty_reason && (
            <div className="bg-orange-50 border border-orange-200 rounded-xl p-3">
              <h5 className="text-[10px] font-bold uppercase text-orange-800">Data Sufficiency Warning</h5>
              <p className="text-[11px] text-orange-700 mt-1 leading-relaxed">{uncertainty_reason}</p>
            </div>
          )}

          {escalated && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2">
              <span className="text-red-500 text-lg">⚠️</span>
              <div>
                <h5 className="text-[10px] font-bold uppercase text-red-800">Escalated by Rules</h5>
                <p className="text-[11px] text-red-700">Safety engine forced triage floor.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-accent-wash/30 border-t border-surface-border pt-3 mt-2 text-center">
        <p className="text-[10px] italic text-surface-muted">
          "The AI recommends. The nurse decides." All scores are clinical recommendations only.
        </p>
      </div>
    </motion.div>
  );
}
