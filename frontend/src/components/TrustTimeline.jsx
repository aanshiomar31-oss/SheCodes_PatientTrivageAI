import { motion } from "framer-motion";

export default function TrustTimeline({ patient }) {
  if (!patient) {
    return (
      <div className="panel p-6 flex items-center justify-center text-center">
        <p className="text-sm text-surface-muted">Select a patient to generate their clinical decision audit trail timeline.</p>
      </div>
    );
  }

  const steps = [
    {
      title: "Patient Arrived",
      time: "T+0m",
      desc: `Intake complete for Stay #${patient.stay_id}. Chief complaint: "${patient.chief_complaint || "None recorded"}"`,
      status: "completed",
      icon: "📥",
    },
    {
      title: "AI Recommendation Engine",
      time: "T+1m",
      desc: `ML stack suggested ${patient.recommended_priority} (Risk score: ${patient.risk_score}/100, Confidence: ${Math.round(patient.confidence * 100)}%).`,
      status: "completed",
      icon: "🧠",
      meta: patient.uncertainty_reason ? `Completeness Warn: ${patient.uncertainty_reason}` : null,
    },
    {
      title: "Clinician Primary Review",
      time: "T+3m",
      desc: patient.overridden
        ? `Clinician reviewed recommendation and decided to adjust priority.`
        : `Clinician approved recommended priority: ${patient.priority}.`,
      status: "completed",
      icon: "👩‍⚕️",
    },
    {
      title: "Priority Resolution (Override)",
      time: "T+4m",
      desc: patient.overridden
        ? `Override executed to ${patient.priority}. Stated cause: "${patient.uncertainty_reason || "Clinical judgment"}"`
        : "No override required. Machine recommendation matched clinical presentation.",
      status: patient.overridden ? "warn" : "neutral",
      icon: patient.overridden ? "✍️" : "✅",
    },
    {
      title: "Queue Re-Assessment Loop",
      time: "Ongoing",
      desc: patient.waited_minutes > 15
        ? `Patient has waited ${Math.round(patient.waited_minutes)}m in queue. Retriage timer checks active.`
        : "Vitals update loop active. No breaches reported.",
      status: "active",
      icon: "⏳",
    },
  ];

  return (
    <div className="panel p-5 space-y-4">
      <div>
        <h3 className="label">Decision Trail & Trust Timeline</h3>
        <p className="text-xs text-surface-muted mt-1">Audit logs mapped to ESI clinical milestones.</p>
      </div>

      <div className="relative border-l-2 border-surface-border ml-3 pl-6 space-y-6 py-2">
        {steps.map((step, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="relative"
          >
            {/* Step Node Icon */}
            <span className="absolute -left-10 top-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-accent-wash border border-surface-border text-sm shadow-sm">
              {step.icon}
            </span>

            {/* Step details */}
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-surface-ink">{step.title}</h4>
                <span className="text-[10px] bg-accent-wash px-2 py-0.5 rounded-md text-surface-muted font-medium">
                  {step.time}
                </span>
              </div>
              <p className="text-xs text-surface-muted leading-relaxed">{step.desc}</p>
              {step.meta && (
                <span className="inline-block text-[10px] text-orange-700 font-semibold bg-orange-50 px-2 py-0.5 rounded mt-1 border border-orange-200">
                  {step.meta}
                </span>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
