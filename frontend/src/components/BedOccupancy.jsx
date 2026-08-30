/**
 * BedOccupancy — occupancy bar derived from current queue size against a
 * configurable department capacity.
 *
 * Honesty note: there is no real hospital bed-management system behind
 * this. `capacity` is a display-only constant. This is clearly labeled
 * "Illustrative" in the UI rather than presented as live bed telemetry,
 * since claiming otherwise would be actively misleading in a clinical
 * command-center context.
 */
export default function BedOccupancy({ occupied, capacity = 40 }) {
  const pct = Math.min(1, occupied / capacity);
  const color = pct >= 0.9 ? "bg-red-500" : pct >= 0.7 ? "bg-orange-500" : "bg-accent-mint";

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-surface-muted">
          Bed occupancy <span className="text-surface-muted">(illustrative)</span>
        </p>
        <p className="text-xs text-surface-muted">
          {occupied} / {capacity}
        </p>
      </div>
      <div className="mt-2 h-2.5 w-full rounded-full bg-slate-100">
        <div
          className={`h-2.5 rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  );
}
