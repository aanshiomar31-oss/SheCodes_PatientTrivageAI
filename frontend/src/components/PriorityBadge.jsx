// Solid fills, not tints. A 15%-alpha badge was readable on the old navy;
// on white it disappears, and an invisible P1 in a 40-row queue is a
// safety problem, not a style problem.
const STYLES = {
  P1: "bg-triage-critical text-surface-ink",
  P2: "bg-triage-urgent text-surface-ink",
  P3: "bg-triage-moderate text-surface-ink",
  P4: "bg-triage-low text-surface-ink",
  P5: "bg-triage-nonurgent text-surface-ink",
};

const LABELS = {
  P1: "P1 · Critical",
  P2: "P2 · Urgent",
  P3: "P3 · Moderate",
  P4: "P4 · Low",
  P5: "P5 · Non-urgent",
};

export default function PriorityBadge({ priority, compact = false }) {
  const style = STYLES[priority] ?? "bg-slate-200 text-slate-600";
  const label = compact ? priority : LABELS[priority] ?? priority;

  return (
    <span className={`pill whitespace-nowrap font-semibold tracking-wide ${style}`}>
      {label}
    </span>
  );
}
