import { motion } from "framer-motion";
import PriorityBadge from "./PriorityBadge.jsx";

// Box-glow reads as a smudge on white. Acuity moves to a solid left edge:
// survives small sizes, dense grids, and a badly calibrated monitor.
const PRIORITY_EDGE = {
  P1: "border-l-[3px] border-l-triage-critical",
  P2: "border-l-[3px] border-l-triage-urgent",
  P3: "border-l-[3px] border-l-triage-moderate",
  P4: "border-l-[3px] border-l-triage-low",
  P5: "border-l-[3px] border-l-triage-nonurgent",
};

export default function PatientCard({ entry, selected = false, onClick, onSelect }) {
  const edge = PRIORITY_EDGE[entry.priority] ?? "";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -2 }}
      onClick={() => onClick?.(entry)}
      className={`panel panel-hover cursor-pointer p-4 ${edge} ${
        selected ? "ring-2 ring-accent-mint" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-surface-ink">Stay #{entry.stay_id}</p>
          <p className="mt-0.5 max-w-[14rem] truncate text-xs text-surface-muted">
            {entry.chief_complaint || "Not documented"}
          </p>
        </div>
        <PriorityBadge priority={entry.priority} compact />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2">
        <div>
          <p className="label">CPS</p>
          <p className="mt-0.5 text-xl font-light tracking-tight text-accent-mintInk">
            {(entry.cps * 100).toFixed(0)}
          </p>
        </div>
        <div>
          <p className="label">Wait</p>
          <p className="mt-0.5 text-xl font-light tracking-tight text-surface-ink">
            {Math.round(entry.waited_minutes)}m
          </p>
        </div>
        <div>
          <p className="label">Conf.</p>
          <p className="mt-0.5 text-xl font-light tracking-tight text-surface-ink">
            {(entry.confidence * 100).toFixed(0)}%
          </p>
        </div>
      </div>

      {entry.overridden && (
        <p className="mt-3 text-xs text-violet-600">
          Overridden from AI recommendation {entry.recommended_priority}
        </p>
      )}

      {onSelect && (
        <label
          className="mt-3 flex items-center gap-2 text-xs text-surface-muted"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onSelect(entry)}
            className="rounded border-surface-border text-accent-mint focus:ring-accent-mint/40"
          />
          Compare
        </label>
      )}
    </motion.div>
  );
}
