import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend } from "recharts";

const OVERRIDE_REASONS_DATA = [
  { name: "Clinical Presentation", count: 42 },
  { name: "Comorbidities", count: 28 },
  { name: "Resource Demand", count: 19 },
  { name: "Vitals Discrepancy", count: 15 },
  { name: "Social Placement", count: 8 },
];

const AGREEMENT_DATA = [
  { name: "AI/Clinician Agree", value: 78, color: "#4CAF50" },
  { name: "Clinician Overrode AI", value: 22, color: "#FF9800" },
];

const WEEKLY_TREND = [
  { day: "Mon", agreement: 80, overrides: 12 },
  { day: "Tue", agreement: 75, overrides: 18 },
  { day: "Wed", agreement: 82, overrides: 10 },
  { day: "Thu", agreement: 79, overrides: 15 },
  { day: "Fri", agreement: 77, overrides: 17 },
  { day: "Sat", agreement: 84, overrides: 9 },
  { day: "Sun", agreement: 81, overrides: 11 },
];

const SHIFT_DISTRIBUTION = [
  { shift: "Day (07:00-15:00)", count: 22 },
  { shift: "Evening (15:00-23:00)", count: 35 },
  { shift: "Night (23:00-07:00)", count: 18 },
];

const AGE_DISTRIBUTION = [
  { group: "Pediatric (<12)", count: 8 },
  { group: "Adolescent (12-17)", count: 12 },
  { group: "Adult (18-64)", count: 25 },
  { group: "Geriatric (65+)", count: 40 },
];

export default function OverrideAnalytics() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agreement Rate Donut Chart */}
        <div className="panel p-5 flex flex-col justify-between">
          <div>
            <h3 className="label">Decision Agreement Rate</h3>
            <p className="text-xs text-surface-muted mt-1">Concurrence between ML suggestions and clinician overrides.</p>
          </div>
          <div className="h-48 relative flex items-center justify-center mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={AGREEMENT_DATA}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {AGREEMENT_DATA.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 12, color: "#1A1D1F" }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute text-center">
              <p className="text-3xl font-extrabold text-surface-ink">78%</p>
              <p className="text-[10px] uppercase text-surface-muted tracking-wider">Concurrence</p>
            </div>
          </div>
          <div className="mt-4 flex justify-around text-xs">
            {AGREEMENT_DATA.map((e) => (
              <div key={e.name} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: e.color }} />
                <span className="text-surface-muted">{e.name} ({e.value}%)</span>
              </div>
            ))}
          </div>
        </div>

        {/* Override Reasons Bar Chart */}
        <div className="panel p-5 lg:col-span-2">
          <h3 className="label">Primary Override Justifications</h3>
          <p className="text-xs text-surface-muted mt-1">Stated causes logged in audit trail by triage staff.</p>
          <div className="h-56 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={OVERRIDE_REASONS_DATA} layout="yaml" margin={{ left: 10, right: 10, top: 10, bottom: 10 }}>
                <XAxis type="number" stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 10 }} />
                <YAxis type="category" dataKey="name" stroke="#8CA397" width={110} tick={{ fill: "#1A1D1F", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 12, color: "#1A1D1F" }} />
                <Bar dataKey="count" fill="#34D07F" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Weekly Trend Line Chart */}
        <div className="panel p-5 lg:col-span-2">
          <h3 className="label">Weekly Decision Trends</h3>
          <p className="text-xs text-surface-muted mt-1">Agreement rates vs override frequency over last 7 days.</p>
          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={WEEKLY_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ECEFF3" vertical={false} />
                <XAxis dataKey="day" stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 11 }} />
                <YAxis stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 12, color: "#1A1D1F" }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line name="Agreement %" type="monotone" dataKey="agreement" stroke="#4CAF50" strokeWidth={3} dot={{ r: 4 }} />
                <Line name="Overrides Count" type="monotone" dataKey="overrides" stroke="#FF9800" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Secondary distribution charts */}
        <div className="panel p-5 flex flex-col justify-between">
          <div>
            <h3 className="label">Overrides by Age Group</h3>
            <p className="text-xs text-surface-muted mt-1">Where clinicians intervene most frequently.</p>
          </div>
          <div className="h-44 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={AGE_DISTRIBUTION} margin={{ left: -20, right: 10, top: 10, bottom: 5 }}>
                <XAxis dataKey="group" stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 10 }} />
                <YAxis stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#fff", border: "1px solid #ECEFF3", borderRadius: 12, color: "#1A1D1F" }} />
                <Bar dataKey="count" fill="#4CAF50" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="border-t border-surface-border pt-2 text-[10px] text-surface-muted text-center">
            *Geriatrics (65+) trigger the highest override rate (mostly upgrading to P2).
          </div>
        </div>
      </div>
    </div>
  );
}
