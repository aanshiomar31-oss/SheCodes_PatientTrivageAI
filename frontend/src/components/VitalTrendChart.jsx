import { Line, LineChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

/**
 * VitalTrendChart — line chart of a patient's vitals over time.
 *
 * Honesty note: `TriageStay` stores one point-in-time vitals snapshot
 * per stay, not a persisted time series (see backend/app/api/routes/
 * queue.py::update_vitals docstring). This component plots `points`
 * accumulated CLIENT-SIDE during the current browser session each time
 * a vitals update is submitted — it is not reading historical data from
 * the server. A refresh loses the trend. A real trend view would need a
 * new persisted observations table, which was intentionally not added
 * silently as part of this frontend build.
 */
export default function VitalTrendChart({ points = [] }) {
  if (points.length < 2) {
    return (
      <p className="text-sm text-surface-muted">
        Trend needs at least two recorded observations this session. Update vitals to add a point.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={points} margin={{ left: 8, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#ECEFF3" />
        <XAxis dataKey="label" tick={{ fill: "#9AA1A9", fontSize: 11 }} />
        <YAxis tick={{ fill: "#9AA1A9", fontSize: 11 }} />
        <Tooltip
          contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 16, fontSize: 12, boxShadow: "0 8px 30px -12px rgba(16,24,40,0.18)", color: "#1A1D1F" }}
          labelStyle={{ color: "#e2e8f0" }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
        <Line type="monotone" dataKey="heart_rate" name="Heart Rate" stroke="#f87171" strokeWidth={2} dot />
        <Line type="monotone" dataKey="resp_rate" name="Resp. Rate" stroke="#facc15" strokeWidth={2} dot />
        <Line type="monotone" dataKey="o2_sat" name="O2 Sat" stroke="#34D07F" strokeWidth={2} dot />
        <Line type="monotone" dataKey="sbp" name="Systolic BP" stroke="#4ade80" strokeWidth={2} dot />
      </LineChart>
    </ResponsiveContainer>
  );
}
