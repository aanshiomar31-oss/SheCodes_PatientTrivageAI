import { useState } from "react";
import { motion } from "framer-motion";
import { submitTriage } from "../services/api.js";

// PatientTriage.ai — Single Patient Triage
//
// The form for the Hybrid Intelligence Layer built in this project:
// rule engine -> stacking ensemble -> uncertainty -> SHAP explanation
// (see backend/ml/predict.py). Distinct from the Dashboard, which shows
// the batch-scored MIMIC-IV-ED cohort — this page scores one patient in
// real time via POST /api/v1/triage and shows the full recommendation,
// including WHY, so it stays reviewable rather than a bare verdict.

const PRIORITY_STYLE = {
  P1: { className: "bg-red-50 text-red-700 border-red-300", ring: "ring-red-200" },
  P2: { className: "bg-orange-50 text-orange-700 border-orange-300", ring: "ring-orange-200" },
  P3: { className: "bg-yellow-50 text-yellow-700 border-yellow-300", ring: "ring-yellow-200" },
  P4: { className: "bg-green-50 text-green-700 border-green-300", ring: "ring-green-200" },
  P5: { className: "bg-blue-50 text-blue-700 border-blue-300", ring: "ring-blue-200" },
};

const EMPTY_FORM = {
  age: "",
  gender: "",
  heartrate: "",
  sbp: "",
  dbp: "",
  resprate: "",
  temperature: "",
  o2sat: "",
  pain: "",
  chief_complaint: "",
  chest_pain: false,
  diaphoresis: false,
  fast_positive: false,
  unresponsive: false,
  seizing: false,
  airway_compromise: false,
  stridor: false,
};

const NUMERIC_FIELDS = ["age", "heartrate", "sbp", "dbp", "resprate", "temperature", "o2sat", "pain"];
const FINDING_FIELDS = [
  ["chest_pain", "Chest pain"],
  ["diaphoresis", "Diaphoresis (sweating)"],
  ["fast_positive", "FAST-positive (stroke signs)"],
  ["unresponsive", "Unresponsive / responds to pain only"],
  ["seizing", "Actively seizing"],
  ["airway_compromise", "Airway compromise"],
  ["stridor", "Stridor"],
];

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
    </label>
  );
}

const inputClass =
  "input";

export default function TriagePage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function loadExample(kind) {
    if (kind === "critical") {
      setForm({
        ...EMPTY_FORM,
        age: "72", gender: "F", heartrate: "118", sbp: "92", dbp: "60",
        resprate: "28", temperature: "38.8", o2sat: "89", pain: "5",
        chief_complaint: "Chest discomfort", diaphoresis: true,
      });
    } else if (kind === "well") {
      setForm({
        ...EMPTY_FORM,
        age: "28", gender: "M", heartrate: "74", sbp: "118", dbp: "76",
        resprate: "15", temperature: "98.2", o2sat: "99", pain: "1",
        chief_complaint: "Minor ankle sprain",
      });
    } else {
      setForm({ ...EMPTY_FORM, heartrate: "105" });
    }
    setResult(null);
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    const payload = {};
    for (const [key, value] of Object.entries(form)) {
      if (NUMERIC_FIELDS.includes(key)) {
        payload[key] = value === "" ? null : Number(value);
      } else if (key === "gender" || key === "chief_complaint") {
        payload[key] = value === "" ? null : value;
      } else {
        payload[key] = value;
      }
    }

    try {
      const data = await submitTriage(payload);
      setResult(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join("; ")
          : detail || "Could not reach the backend API. Make sure it's running."
      );
    } finally {
      setSubmitting(false);
    }
  }

  const style = result ? PRIORITY_STYLE[result.priority] ?? PRIORITY_STYLE.P3 : null;

  return (
    <div className="space-y-6">
      <div className="panel p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-surface-ink">Single patient triage</h2>
            <p className="mt-1 text-sm text-surface-muted">
              Rule engine runs first and can only escalate. The ensemble explains what it saw.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => loadExample("critical")}
              className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Load critical example
            </button>
            <button
              type="button"
              onClick={() => loadExample("well")}
              className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Load well-patient example
            </button>
            <button
              type="button"
              onClick={() => loadExample("sparse")}
              className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
            >
              Load near-empty example
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Field label="Age">
            <input type="number" min="0" max="120" step="0.1" className={inputClass}
              value={form.age} onChange={(e) => update("age", e.target.value)} />
          </Field>
          <Field label="Gender">
            <select className={inputClass} value={form.gender} onChange={(e) => update("gender", e.target.value)}>
              <option value="">—</option>
              <option value="F">F</option>
              <option value="M">M</option>
            </select>
          </Field>
          <Field label="Heart rate (bpm)">
            <input type="number" className={inputClass} value={form.heartrate}
              onChange={(e) => update("heartrate", e.target.value)} />
          </Field>
          <Field label="Resp. rate (/min)">
            <input type="number" className={inputClass} value={form.resprate}
              onChange={(e) => update("resprate", e.target.value)} />
          </Field>
          <Field label="Systolic BP">
            <input type="number" className={inputClass} value={form.sbp}
              onChange={(e) => update("sbp", e.target.value)} />
          </Field>
          <Field label="Diastolic BP">
            <input type="number" className={inputClass} value={form.dbp}
              onChange={(e) => update("dbp", e.target.value)} />
          </Field>
          <Field label="O2 saturation (%)">
            <input type="number" min="0" max="100" className={inputClass} value={form.o2sat}
              onChange={(e) => update("o2sat", e.target.value)} />
          </Field>
          <Field label="Temperature (°C or °F)">
            <input type="number" step="0.1" className={inputClass} value={form.temperature}
              onChange={(e) => update("temperature", e.target.value)} />
          </Field>
          <Field label="Pain (0-10)">
            <input type="number" min="0" max="10" className={inputClass} value={form.pain}
              onChange={(e) => update("pain", e.target.value)} />
          </Field>
          <div className="col-span-2 sm:col-span-4">
            <Field label="Chief complaint">
              <input type="text" className={inputClass} value={form.chief_complaint}
                onChange={(e) => update("chief_complaint", e.target.value)}
                placeholder="e.g. Chest discomfort" />
            </Field>
          </div>

          <div className="col-span-2 sm:col-span-4">
            <span className="text-xs font-medium text-slate-600">Clinical findings observed at intake</span>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {FINDING_FIELDS.map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={form[key]}
                    onChange={(e) => update(key, e.target.checked)}
                    className="rounded border-surface-border"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>

          <div className="col-span-2 sm:col-span-4">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-surface-ink hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Scoring…" : "Get triage recommendation"}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}
      </div>

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className={`rounded-xl border p-6 shadow-sm ring-4 ${style.className} ${style.ring}`}
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide">Priority</p>
              <p className="text-4xl font-bold">{result.priority}</p>
              {result.escalated && (
                <span className="mt-1 inline-flex items-center rounded-full bg-white/70 px-2.5 py-0.5 text-xs font-semibold">
                  ⚠ Escalated by rule engine
                </span>
              )}
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold uppercase tracking-wide">Risk score</p>
              <p className="text-3xl font-bold">{result.risk_score}/100</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold uppercase tracking-wide">Confidence</p>
              <p className="text-3xl font-bold">{(result.confidence * 100).toFixed(0)}%</p>
            </div>
          </div>

          {result.uncertainty_reason && (
            <p className="mt-4 rounded-lg bg-white/60 px-3 py-2 text-sm">
              <span className="font-semibold">Why confidence is limited: </span>
              {result.uncertainty_reason}
            </p>
          )}

          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-wide">Top contributing factors</p>
            <ul className="mt-2 space-y-1">
              {result.top_features.map((f, i) => (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/70 text-xs font-bold">
                    {i + 1}
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>

          <p className="mt-5 border-t border-white/50 pt-3 text-xs font-medium">{result.governing_rule}</p>
        </motion.div>
      )}
    </div>
  );
}
