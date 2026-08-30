import { AnimatePresence, motion } from "framer-motion";

/**
 * LiveAlert — banner list for currently-escalated (P1) patients.
 * Purely informational: clicking never moves a patient or changes
 * anything, consistent with "the AI recommends, the nurse decides."
 */
export default function LiveAlert({ alerts = [], onSelect }) {
  if (alerts.length === 0) {
    return (
      <div className="panel px-4 py-3 text-sm text-surface-muted">
        No active critical alerts.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <AnimatePresence>
        {alerts.map((alert) => (
          <motion.button
            key={alert.stay_id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            onClick={() => onSelect?.(alert)}
            className="flex w-full items-center justify-between rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-left transition hover:bg-red-100"
          >
            <div>
              <p className="text-sm font-semibold text-red-600">
                {alert.priority} · Stay #{alert.stay_id}
              </p>
              <p className="text-xs text-red-200/80">{alert.chief_complaint || "No complaint documented"}</p>
            </div>
            <span className="text-xs font-medium text-red-600">{Math.round(alert.waited_minutes)}m waiting</span>
          </motion.button>
        ))}
      </AnimatePresence>
    </div>
  );
}
