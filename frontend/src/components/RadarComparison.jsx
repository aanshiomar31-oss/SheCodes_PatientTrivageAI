import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend, Tooltip } from "recharts";

// Clinically reasonable ranges used ONLY to normalize each vital onto a
// shared 0-100 radar axis — raw units differ too much (SpO2 0-100 vs HR
// 40-200 vs Temp 95-105) to plot together meaningfully otherwise. The
// tooltip always shows the real unit value, never just the normalized one.
const RANGES = {
  heart_rate: { min: 40, max: 180, label: "Heart Rate" },
  resp_rate: { min: 8, max: 40, label: "Resp. Rate" },
  sbp: { min: 60, max: 200, label: "Systolic BP" },
  o2_sat: { min: 70, max: 100, label: "O2 Saturation" },
  temperature: { min: 95, max: 105, label: "Temperature" },
  pain: { min: 0, max: 10, label: "Pain" },
};

const COLORS = ["#34D07F", "#f472b6", "#facc15", "#4ade80"];

function normalize(value, key) {
  if (value === null || value === undefined) return 0;
  const { min, max } = RANGES[key];
  return Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
}

/**
 * RadarComparison — up to 4 patients overlaid on one radar. Each axis is
 * a vital, normalized to 0-100 for shared scale; hover to see real units.
 */
export default function RadarComparison({ patients }) {
  if (!patients || patients.length === 0) {
    return <p className="text-sm text-surface-muted">Select patients to compare.</p>;
  }

  const data = Object.entries(RANGES).map(([key, { label }]) => {
    const row = { vital: label };
    patients.forEach((p, i) => {
      row[`p${i}`] = normalize(p[key], key);
      row[`p${i}_raw`] = p[key] ?? "—";
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={360}>
      <RadarChart data={data} outerRadius="75%">
        <PolarGrid stroke="#ECEFF3" />
        <PolarAngleAxis dataKey="vital" tick={{ fill: "#9AA1A9", fontSize: 12 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#475569", fontSize: 10 }} />
        {patients.map((p, i) => (
          <Radar
            key={p.stay_id}
            name={`Stay #${p.stay_id}`}
            dataKey={`p${i}`}
            stroke={COLORS[i % COLORS.length]}
            fill={COLORS[i % COLORS.length]}
            fillOpacity={0.15}
            strokeWidth={2}
          />
        ))}
        <Legend wrapperStyle={{ fontSize: 12, color: "#94a3b8" }} />
        <Tooltip
          contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 16, fontSize: 12, boxShadow: "0 8px 30px -12px rgba(16,24,40,0.18)", color: "#1A1D1F" }}
          labelStyle={{ color: "#e2e8f0" }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
