import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const CERTIFICATION_STEPS = [
  {
    title: "Clinical Trust Principle",
    icon: "🤝",
    content: "The AI is a support tool, not a decision-maker. The recommendation engine sets ESI floor constraints but never autonomously persists patient triage or moves patients. Clinicians override recommendations anytime.",
    checkpoint: "I understand that the clinician holds final accountability.",
  },
  {
    title: "Rule-Engine Priority Floor",
    icon: "🛡️",
    content: "If a patient triggers a red-flag rule (e.g., Stroke symptoms/FAST-positive, Oxygen saturation <90%), the system clamps the recommended acuity to P1/P2. The ML ensemble cannot soften this ceiling.",
    checkpoint: "I understand how safety clamps prevent critical under-triage.",
  },
  {
    title: "Missing Data & Uncertainty",
    icon: "❓",
    content: "Unlike standard ML classifiers, this system penalizes missing vital signs by lowering certainty. Age and gender alone do not trigger predictions, and blank fields reduce confidence instead of being treated as normal.",
    checkpoint: "I understand how missing vitals lower prediction confidence.",
  },
  {
    title: "Interactive Demo Patient Case",
    icon: "📋",
    content: "Let's review a clinical case: A 72-year-old female presenting with sudden facial droop (FAST-positive), SBP 165, DBP 95, SpO2 98%. The AI recommends P1 due to stroke protocol activation, despite normal oxygenation.",
    checkpoint: "I have reviewed the stroke case study and rule floor trigger.",
  }
];

export default function TrainingPanel() {
  const [currentStep, setCurrentStep] = useState(0);
  const [certifiedSteps, setCertifiedSteps] = useState({});
  const [progress, setProgress] = useState(0);
  const [completed, setCompleted] = useState(false);

  const toggleCheck = (idx) => {
    const nextCertified = { ...certifiedSteps, [idx]: !certifiedSteps[idx] };
    setCertifiedSteps(nextCertified);

    // Calculate progress
    const checkedCount = Object.values(nextCertified).filter(Boolean).length;
    const computedProgress = Math.round((checkedCount / CERTIFICATION_STEPS.length) * 100);
    setProgress(computedProgress);

    if (checkedCount === CERTIFICATION_STEPS.length) {
      setCompleted(true);
    } else {
      setCompleted(false);
    }
  };

  const nextStep = () => {
    if (currentStep < CERTIFICATION_STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  return (
    <div className="panel p-5 space-y-6">
      <div className="flex justify-between items-center border-b border-surface-border pb-3">
        <div>
          <h3 className="label">Clinician Trust & Safety Certification</h3>
          <p className="text-xs text-surface-muted mt-1">Review core CDSS guidelines to complete onboarding.</p>
        </div>
        <div className="text-right">
          <span className="text-xs font-bold text-accent-mintInk">{progress}% Complete</span>
          <div className="w-24 bg-accent-wash h-1.5 rounded-full overflow-hidden mt-1 border border-surface-border">
            <div className="bg-accent-mint h-full transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>

      {/* Onboarding Wizard */}
      <div className="bg-accent-wash border border-surface-border rounded-xl p-5 min-h-[180px] flex flex-col justify-between">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="space-y-3"
          >
            <div className="flex items-center gap-2">
              <span className="text-2xl">{CERTIFICATION_STEPS[currentStep].icon}</span>
              <h4 className="text-sm font-bold text-surface-ink">
                {currentStep + 1}. {CERTIFICATION_STEPS[currentStep].title}
              </h4>
            </div>
            <p className="text-xs text-surface-muted leading-relaxed">
              {CERTIFICATION_STEPS[currentStep].content}
            </p>
          </motion.div>
        </AnimatePresence>

        <div className="mt-4 flex items-center justify-between border-t border-surface-border pt-4">
          <div className="flex gap-2">
            <button
              onClick={prevStep}
              disabled={currentStep === 0}
              className="px-3 py-1.5 rounded-lg text-xs bg-[#FAFBFC] border border-surface-border text-slate-700 hover:bg-slate-100 disabled:opacity-30 font-medium"
            >
              Back
            </button>
            <button
              onClick={nextStep}
              disabled={currentStep === CERTIFICATION_STEPS.length - 1}
              className="px-3 py-1.5 rounded-lg text-xs bg-[#FAFBFC] border border-surface-border text-slate-700 hover:bg-slate-100 disabled:opacity-30 font-medium"
            >
              Next
            </button>
          </div>

          <label className="flex items-center gap-2 cursor-pointer bg-white border border-accent-mint/30 rounded-xl px-3 py-2">
            <input
              type="checkbox"
              checked={!!certifiedSteps[currentStep]}
              onChange={() => toggleCheck(currentStep)}
              className="rounded border-accent-mint text-accent-blue focus:ring-accent-blue"
            />
            <span className="text-xs text-accent-mintInk font-semibold">
              Sign off Checkpoint
            </span>
          </label>
        </div>
      </div>

      {completed && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-accent-wash border border-accent-mint/40 rounded-xl p-4 text-center space-y-2"
        >
          <p className="text-sm font-bold text-accent-mintInk">🎉 Clinician CDSS Clearance Completed</p>
          <p className="text-xs text-surface-muted">You are now authorized to triage and record overrides on active emergency patients.</p>
        </motion.div>
      )}
    </div>
  );
}
