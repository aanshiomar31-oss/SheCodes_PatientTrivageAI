import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// PatientTriage.ai — Acuity Distribution Chart
//
// Colors match the acuity badges in TriageStayTable.jsx and the palette
// reserved in tailwind.config.js, so acuity reads identically wherever
// it appears in the app.

const ACUITY_COLORS = {
  "1": "#dc2626",
  "2": "#ea580c",
  "3": "#ca8a04",
  "4": "#16a34a",
  "5": "#2563eb",
  "(none)": "#94a3b8",
};

const ACUITY_LABELS = {
  "1": "1 · Critical",
  "2": "2 · Urgent",
  "3": "3 · Moderate",
  "4": "4 · Low",
  "5": "5 · Non-urgent",
  "(none)": "Untriaged",
};

export default function AcuityChart({ acuityCounts }) {
  const order = ["1", "2", "3", "4", "5", "(none)"];
  const data = order
    .filter((key) => acuityCounts?.[key])
    .map((key) => ({
      key,
      label: ACUITY_LABELS[key] ?? key,
      count: acuityCounts[key],
      color: ACUITY_COLORS[key] ?? "#94a3b8",
    }));

  if (data.length === 0) {
    return <p className="text-sm text-surface-muted">No acuity data available.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#ECEFF3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} />
        <Tooltip
          cursor={{ fill: "#f8fafc" }}
          contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13 }}
        />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry.key} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
