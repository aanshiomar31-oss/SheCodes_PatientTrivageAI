import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const BAR_COLOR = "#34D07F";

/**
 * SHAPPanel — two modes:
 *
 * `mode="global"` — real SHAP mean(|value|) magnitudes from the trained
 * ensemble (backend/reports/feature_importance.json via
 * GET /model/feature-importance). Numeric bars are genuine.
 *
 * `mode="patient"` — POST /triage's `top_features` is an ORDERED list of
 * human-readable reasons, not signed SHAP magnitudes (the API contract
 * intentionally doesn't expose per-call numeric SHAP values — see
 * backend/ml/predict.py). Bars here are rank-based (1st reason = widest)
 * rather than fabricated numbers, so nothing here misrepresents itself
 * as more precise than it is.
 */
export default function SHAPPanel({ mode = "global", data = [] }) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-surface-muted">No explanation data available yet.</p>;
  }

  if (mode === "global") {
    const chartData = data
      .slice(0, 12)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);

    return (
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 24, right: 16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#ECEFF3" horizontal={false} />
          <XAxis type="number" tick={{ fill: "#9AA1A9", fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={150} tick={{ fill: "#cbd5e1", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 16, fontSize: 12, boxShadow: "0 8px 30px -12px rgba(16,24,40,0.18)", color: "#1A1D1F" }}
            labelStyle={{ color: "#e2e8f0" }}
            formatter={(v) => [v.toFixed(4), "Mean |SHAP|"]}
          />
          <Bar dataKey="value" radius={[0, 6, 6, 0]}>
            {chartData.map((_, i) => (
              <Cell key={i} fill={BAR_COLOR} fillOpacity={1 - i * 0.06} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // mode === "patient": ordinal ranking, not fabricated magnitudes.
  return (
    <ul className="space-y-2">
      {data.map((reason, i) => (
        <li key={i} className="flex items-center gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-wash text-xs font-bold text-accent-mintInk">
            {i + 1}
          </span>
          <div className="flex-1">
            <div className="h-2 rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full bg-sky-400"
                style={{ width: `${100 - i * 25}%` }}
              />
            </div>
          </div>
          <span className="w-56 shrink-0 text-sm text-surface-ink">{reason}</span>
        </li>
      ))}
    </ul>
  );
}
