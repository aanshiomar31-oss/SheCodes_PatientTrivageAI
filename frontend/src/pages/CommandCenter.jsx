import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchQueue } from "../services/api.js";
import { useLiveSocket } from "../hooks/useLiveSocket.js";
import { useSurge } from "../context/SurgeContext.jsx";
import LiveAlert from "../components/LiveAlert.jsx";
import BedOccupancy from "../components/BedOccupancy.jsx";
import SurgeToggle from "../components/SurgeToggle.jsx";
import PriorityBadge from "../components/PriorityBadge.jsx";

const NURSES_ON_SHIFT = 4; // illustrative staffing constant — no roster backend exists
const BED_CAPACITY = 40;
const POLL_MS = 20000; // fallback only — the WebSocket is the primary refresh trigger

function KPICard({ label, value, sub, accent = "text-surface-ink", delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className="panel panel-hover p-5"
    >
      <p className="label">{label}</p>
      <p className={`mt-2 stat ${accent}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-surface-muted">{sub}</p>}
    </motion.div>
  );
}

export default function CommandCenter() {
  const { surge } = useSurge();
  const [queue, setQueue] = useState(null);
  const [error, setError] = useState(null);
  const inFlightRef = useRef(false);

  // Overlap guard — see the matching comment in LiveQueue.jsx for why
  // this exists: a slow /queue response plus a fixed timer previously
  // let requests pile up indefinitely under load.
  function refresh() {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    fetchQueue("priority")
      .then((data) => setQueue(data))
      .catch(() => setError("Could not reach the backend API."))
      .finally(() => {
        inFlightRef.current = false;
      });
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  const { connected } = useLiveSocket({
    new_patient: refresh,
    override: refresh,
    vitals_updated: refresh,
    // reassessment_alert is purely informational — predict() is
    // deterministic given the same DB row, so nothing changed and a
    // full queue rescan accomplishes nothing except wasted work. It's
    // shown as a toast only. (Refreshing here previously caused a
    // runaway loop: every P1 patient re-alerted every monitor cycle,
    // and each alert triggered a full re-score of the whole queue.)
  });

  if (error) {
    return (
      <div className="panel border-red-200 bg-red-50 p-6 text-sm text-red-600">{error}</div>
    );
  }

  const entries = queue?.entries ?? [];
  const critical = entries.filter((e) => e.priority === "P1" || e.priority === "P2");
  const avgWait = entries.length
    ? Math.round(entries.reduce((sum, e) => sum + e.waited_minutes, 0) / entries.length)
    : 0;
  const alerts = entries.filter((e) => e.priority === "P1").sort((a, b) => b.waited_minutes - a.waited_minutes);
  const displayCount = surge ? entries.length * 3 : entries.length; // display-only, see SurgeContext

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-surface-ink">
            Command Center
            <span className={`inline-flex items-center gap-1 text-xs font-normal ${connected ? "text-accent-mintInk" : "text-surface-muted"}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-accent-mint" : "bg-slate-500"}`} />
              {connected ? "Live" : "Reconnecting…"}
            </span>
          </h1>
          <p className="text-sm text-surface-muted">Live overview of the Emergency Department queue.</p>
        </div>
        <SurgeToggle />
      </div>

      {surge && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Surge Mode is a display simulation only — see the Digital Twin page. Scoring thresholds never change under surge.
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <KPICard label="Waiting patients" value={displayCount} delay={0} />
        <KPICard label="Critical (P1/P2)" value={critical.length * (surge ? 3 : 1)} accent="text-red-500" delay={0.05} />
        <KPICard label="Average wait" value={`${avgWait}m`} delay={0.1} />
        <KPICard label="Nurses on shift" value={NURSES_ON_SHIFT} sub="illustrative" delay={0.15} />
        <KPICard
          label="Workload / nurse"
          value={(displayCount / NURSES_ON_SHIFT).toFixed(1)}
          sub="patients per nurse"
          delay={0.2}
        />
        <KPICard label="Model" value={queue ? "Live" : "…"} accent="text-accent-mintInk" delay={0.25} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="panel p-5 lg:col-span-2">
          <h2 className="label">Live alerts</h2>
          <p className="mt-1 text-xs text-surface-muted">P1 patients, longest-waiting first.</p>
          <div className="mt-4">
            <LiveAlert alerts={alerts} />
          </div>
        </div>

        <div className="space-y-4">
          <div className="panel p-5">
            <BedOccupancy occupied={Math.min(BED_CAPACITY, entries.length)} capacity={BED_CAPACITY} />
          </div>
          <div className="panel p-5">
            <h3 className="label">Priority mix</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {["P1", "P2", "P3", "P4", "P5"].map((p) => (
                <div key={p} className="flex items-center gap-1.5">
                  <PriorityBadge priority={p} compact />
                  <span className="text-xs text-surface-muted">{entries.filter((e) => e.priority === p).length}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="panel p-5">
          <h3 className="label">Priority distribution</h3>
          <PriorityDistributionChart entries={entries} />
        </div>
        <div className="panel p-5">
          <h3 className="label">Wait time distribution</h3>
          <WaitTimeHistogram entries={entries} />
        </div>
      </div>
    </div>
  );
}

function PriorityDistributionChart({ entries }) {
  const colors = { P1: "#f87171", P2: "#fb923c", P3: "#facc15", P4: "#4ade80", P5: "#60a5fa" };
  const data = ["P1", "P2", "P3", "P4", "P5"].map((p) => ({
    priority: p, count: entries.filter((e) => e.priority === p).length,
  }));
  if (entries.length === 0) return <p className="mt-4 text-sm text-surface-muted">No data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#ECEFF3" vertical={false} />
        <XAxis dataKey="priority" tick={{ fill: "#9AA1A9", fontSize: 12 }} axisLine={{ stroke: "#E4E8EE" }} />
        <YAxis allowDecimals={false} tick={{ fill: "#9AA1A9", fontSize: 12 }} axisLine={{ stroke: "#E4E8EE" }} />
        <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 16, fontSize: 12, boxShadow: "0 8px 30px -12px rgba(16,24,40,0.18)", color: "#1A1D1F" }} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((d) => <Cell key={d.priority} fill={colors[d.priority]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function WaitTimeHistogram({ entries }) {
  const buckets = [
    { label: "0-10m", max: 10 }, { label: "10-30m", max: 30 }, { label: "30-60m", max: 60 },
    { label: "60-120m", max: 120 }, { label: "120m+", max: Infinity },
  ];
  const data = buckets.map((b, i) => {
    const min = i === 0 ? 0 : buckets[i - 1].max;
    return { label: b.label, count: entries.filter((e) => e.waited_minutes >= min && e.waited_minutes < b.max).length };
  });
  if (entries.length === 0) return <p className="mt-4 text-sm text-surface-muted">No data yet.</p>;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#ECEFF3" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: "#9AA1A9", fontSize: 11 }} axisLine={{ stroke: "#E4E8EE" }} />
        <YAxis allowDecimals={false} tick={{ fill: "#9AA1A9", fontSize: 12 }} axisLine={{ stroke: "#E4E8EE" }} />
        <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 16, fontSize: 12, boxShadow: "0 8px 30px -12px rgba(16,24,40,0.18)", color: "#1A1D1F" }} />
        <Bar dataKey="count" fill="#34D07F" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
