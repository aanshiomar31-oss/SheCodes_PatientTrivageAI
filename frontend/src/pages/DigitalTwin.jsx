import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useSurge } from "../context/SurgeContext.jsx";
import SurgeToggle from "../components/SurgeToggle.jsx";
import PriorityBadge from "../components/PriorityBadge.jsx";

// PatientTriage.ai — Digital Twin
//
// Honesty note: this is a CLIENT-SIDE simulation. The real backend has
// no bed-management, nurse-roster, or arrival-generation system to
// drive a server-side twin from (see BedOccupancy.jsx and CommandCenter
// for the same caveat on real KPI cards). This page exists to visually
// demonstrate how the department behaves under load — arrivals, beds
// filling, nurses stretched thin, waiting-room deterioration — using
// the SAME clinical logic conventions (priority colors, CPS-style
// urgency) as the rest of the app, without claiming to read live
// hospital telemetry that doesn't exist.

const BED_CAPACITY = 24;
const NURSES = 4;
const PRIORITIES = ["P1", "P2", "P3", "P4", "P5"];
const PRIORITY_WEIGHTS = [0.06, 0.16, 0.35, 0.30, 0.13]; // roughly matches the real cohort's mix

function weightedPriority() {
  const r = Math.random();
  let cumulative = 0;
  for (let i = 0; i < PRIORITIES.length; i++) {
    cumulative += PRIORITY_WEIGHTS[i];
    if (r < cumulative) return PRIORITIES[i];
  }
  return "P5";
}

let idCounter = 1;

export default function DigitalTwin() {
  const { surge } = useSurge();
  const [beds, setBeds] = useState([]); // occupied beds: [{id, priority, enteredAt}]
  const [waiting, setWaiting] = useState([]); // waiting room: [{id, priority, arrivedAt}]
  const [tick, setTick] = useState(0);
  const [running, setRunning] = useState(true);
  const [log, setLog] = useState([]);
  const tickRef = useRef(0);

  function pushLog(text) {
    setLog((prev) => [{ id: Date.now() + Math.random(), text, t: prev.length }, ...prev].slice(0, 12));
  }

  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => {
      tickRef.current += 1;
      setTick(tickRef.current);

      const arrivalChance = surge ? 0.55 : 0.22;
      setWaiting((prev) => {
        let next = [...prev];
        if (Math.random() < arrivalChance) {
          const priority = weightedPriority();
          const patient = { id: idCounter++, priority, arrivedAt: tickRef.current };
          next = [...next, patient];
          if (priority === "P1" || priority === "P2") {
            pushLog(`New arrival: ${priority} patient — high priority`);
          }
        }
        return next;
      });

      // Waiting-room deterioration: a patient waiting too long may escalate.
      setWaiting((prev) =>
        prev.map((p) => {
          const waited = tickRef.current - p.arrivedAt;
          if (waited > 6 && p.priority !== "P1" && Math.random() < 0.05) {
            const idx = PRIORITIES.indexOf(p.priority);
            const escalated = PRIORITIES[Math.max(0, idx - 1)];
            pushLog(`Deterioration: waiting patient escalated ${p.priority} → ${escalated}. Recommended reassessment.`);
            return { ...p, priority: escalated };
          }
          return p;
        })
      );
    }, surge ? 700 : 1400);
    return () => clearInterval(interval);
  }, [running, surge]);

  // Move patients from waiting into beds as capacity allows, most urgent first.
  useEffect(() => {
    setBeds((prevBeds) => {
      const free = BED_CAPACITY - prevBeds.length;
      if (free <= 0) return prevBeds;
      let admitted = [...prevBeds];
      setWaiting((prevWaiting) => {
        const sorted = [...prevWaiting].sort((a, b) => PRIORITIES.indexOf(a.priority) - PRIORITIES.indexOf(b.priority));
        const toAdmit = sorted.slice(0, free);
        const remaining = prevWaiting.filter((p) => !toAdmit.includes(p));
        admitted = [...admitted, ...toAdmit.map((p) => ({ ...p, enteredAt: tickRef.current }))];
        return remaining;
      });
      return admitted;
    });

    // Discharge occasionally to free beds.
    const dischargeChance = surge ? 0.12 : 0.2;
    if (Math.random() < dischargeChance) {
      setBeds((prev) => (prev.length > 0 ? prev.slice(1) : prev));
    }
  }, [tick, surge]);

  const occupancyPct = Math.min(1, beds.length / BED_CAPACITY);
  const workload = (waiting.length / NURSES).toFixed(1);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-surface-ink">Digital Twin</h1>
          <p className="text-sm text-surface-muted">
            Simulated department dynamics — client-side, illustrative, not live hospital telemetry.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setRunning((r) => !r)}
            className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-surface-ink hover:bg-slate-50">
            {running ? "Pause" : "Resume"}
          </button>
          <SurgeToggle />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Waiting room" value={waiting.length} accent="text-orange-300" />
        <Stat label="Beds occupied" value={`${beds.length}/${BED_CAPACITY}`} accent="text-accent-mintInk" />
        <Stat label="Occupancy" value={`${Math.round(occupancyPct * 100)}%`} accent={occupancyPct > 0.85 ? "text-red-500" : "text-accent-mintInk"} />
        <Stat label="Workload / nurse" value={workload} accent="text-violet-600" />
      </div>

      {surge && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Surge Mode active — arrival rate ~3× baseline. Recommendations and reassessment continue on the same clinical logic; nothing about scoring itself has changed.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="panel p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Beds ({beds.length}/{BED_CAPACITY})</h2>
          <div className="mt-4 grid grid-cols-6 gap-2 sm:grid-cols-8">
            {Array.from({ length: BED_CAPACITY }).map((_, i) => {
              const patient = beds[i];
              return (
                <motion.div
                  key={i}
                  layout
                  className={`flex h-12 items-center justify-center rounded-lg border text-xs font-semibold ${
                    patient
                      ? PRIORITY_CELL[patient.priority]
                      : "border-surface-border bg-white text-slate-600"
                  }`}
                >
                  {patient ? patient.priority : "—"}
                </motion.div>
              );
            })}
          </div>

          <h2 className="mt-6 text-sm font-semibold uppercase tracking-wide text-slate-600">Waiting room</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <AnimatePresence>
              {waiting.map((p) => (
                <motion.div
                  key={p.id}
                  layout
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="flex items-center gap-2 rounded-full border border-surface-border bg-[#FAFBFC] px-3 py-1.5"
                >
                  <PriorityBadge priority={p.priority} compact />
                  <span className="text-xs text-surface-muted">{tick - p.arrivedAt}m</span>
                </motion.div>
              ))}
            </AnimatePresence>
            {waiting.length === 0 && <p className="text-sm text-surface-muted">Waiting room empty.</p>}
          </div>
        </div>

        <div className="panel p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Simulation events</h2>
          <div className="mt-3 space-y-2">
            <AnimatePresence>
              {log.map((entry) => (
                <motion.p
                  key={entry.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="rounded-lg bg-white px-3 py-2 text-xs text-slate-600"
                >
                  {entry.text}
                </motion.p>
              ))}
            </AnimatePresence>
            {log.length === 0 && <p className="text-sm text-surface-muted">No events yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

const PRIORITY_CELL = {
  P1: "border-red-500/60 bg-red-500/20 text-red-600",
  P2: "border-orange-500/60 bg-orange-500/20 text-orange-300",
  P3: "border-yellow-500/60 bg-yellow-500/20 text-yellow-300",
  P4: "border-green-500/60 bg-green-500/20 text-green-300",
  P5: "border-blue-500/60 bg-blue-500/20 text-blue-300",
};

function Stat({ label, value, accent }) {
  return (
    <div className="panel p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-surface-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}
