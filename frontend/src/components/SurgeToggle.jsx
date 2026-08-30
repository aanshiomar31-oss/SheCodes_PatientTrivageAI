import { useSurge } from "../context/SurgeContext.jsx";

/**
 * SurgeToggle — engages the client-side surge simulation (see
 * SurgeContext). Never changes scoring thresholds; only display density
 * and the Digital Twin's arrival rate.
 */
export default function SurgeToggle() {
  const { surge, setSurge } = useSurge();

  return (
    <button
      onClick={() => setSurge(!surge)}
      className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
        surge
          ? "bg-violet-500 text-surface-ink shadow-card"
          : "border border-surface-border text-slate-600 hover:bg-slate-50"
      }`}
    >
      {surge ? "⚠ Surge Mode: ON (3×)" : "Simulate 3× Surge"}
    </button>
  );
}
