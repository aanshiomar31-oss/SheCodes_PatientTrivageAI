import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { submitTriage } from "../services/api.js";
import PriorityBadge from "../components/PriorityBadge.jsx";
import ConfidenceGauge from "../components/ConfidenceGauge.jsx";
import SepsisAlert from "../components/SepsisAlert.jsx";
import ProtocolModal from "../components/ProtocolModal.jsx";

const EMPTY_FORM = {
  age: "", gender: "", returning_patient: false, history: "",
  heartrate: "", sbp: "", dbp: "", resprate: "", temperature: "", o2sat: "", pain: "",
  chief_complaint: "",
  chest_pain: false, diaphoresis: false, fast_positive: false,
  unresponsive: false, seizing: false, airway_compromise: false, stridor: false,
};

const NUMERIC_FIELDS = ["age", "heartrate", "sbp", "dbp", "resprate", "temperature", "o2sat", "pain"];
const FINDING_FIELDS = [
  ["chest_pain", "Chest pain"], ["diaphoresis", "Diaphoresis"], ["fast_positive", "FAST-positive"],
  ["unresponsive", "Unresponsive"], ["seizing", "Seizing"], ["airway_compromise", "Airway compromise"],
  ["stridor", "Stridor"],
];

const inputClass = "input";

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-surface-muted">{label}</span>
      {children}
    </label>
  );
}

function buildPayload(form) {
  const payload = {};
  for (const [key, value] of Object.entries(form)) {
    if (NUMERIC_FIELDS.includes(key)) payload[key] = value === "" ? null : Number(value);
    else if (key === "gender" || key === "chief_complaint") payload[key] = value === "" ? null : value;
    else if (key === "returning_patient" || key === "history") continue; // not part of the /triage contract; intake-only context
    else payload[key] = value;
  }
  return payload;
}

function hasEnoughSignal(form) {
  // Age and gender alone carry no actionable clinical signal — at least one
  // vital sign or a chief complaint is required before hitting the backend.
  const vitals = ["heartrate", "sbp", "dbp", "resprate", "temperature", "o2sat"];
  const hasVital = vitals.some((k) => form[k] !== "");
  const hasComplaint = form.chief_complaint.trim() !== "";
  const hasFinding = ["chest_pain", "diaphoresis", "fast_positive", "unresponsive", "seizing", "airway_compromise", "stridor"].some(
    (k) => form[k] === true
  );
  return hasVital || hasComplaint || hasFinding;
}

export default function PatientIntake() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [preview, setPreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitted, setSubmitted] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [showProtocols, setShowProtocols] = useState(false);
  const debounceRef = useRef(null);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  // Live AI preview: debounced re-score on every field change, distinct
  // from the final submit — this is the "as fields change, show live AI
  // preview" requirement. Preview calls the same POST /triage endpoint
  // as submit; nothing about it is faked.
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!hasEnoughSignal(form)) {
      setPreview(null);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setPreviewLoading(true);
      try {
        const data = await submitTriage(buildPayload(form));
        setPreview(data);
      } catch {
        setPreview(null);
      } finally {
        setPreviewLoading(false);
      }
    }, 600);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(form)]);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const data = await submitTriage(buildPayload(form));
      setSubmitted(data);
      // Show protocol modal immediately on submit if any protocols fired
      if (data.triggered_protocols?.length > 0) setShowProtocols(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const displayed = submitted ?? preview;

  return (
    <>
      {/* Protocol modal — full screen takeover on time-critical triggers */}
      {showProtocols && submitted?.triggered_protocols?.length > 0 && (
        <ProtocolModal
          protocols={submitted.triggered_protocols}
          patientId={submitted.patient_id}
          onClose={() => setShowProtocols(false)}
        />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <form onSubmit={handleSubmit} className="space-y-6 lg:col-span-2">
        <div className="panel p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Demographics</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
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
            <Field label="Returning patient">
              <div className="mt-2">
                <input type="checkbox" checked={form.returning_patient}
                  onChange={(e) => update("returning_patient", e.target.checked)}
                  className="rounded border-surface-border" />
              </div>
            </Field>
            <div className="col-span-2 sm:col-span-1">
              <Field label="History notes">
                <input type="text" className={inputClass} value={form.history}
                  onChange={(e) => update("history", e.target.value)} placeholder="Context, not scored directly" />
              </Field>
            </div>
          </div>
        </div>

        <div className="panel p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Vitals</h2>
          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Field label="Heart rate (bpm)">
              <input type="number" className={inputClass} value={form.heartrate}
                onChange={(e) => update("heartrate", e.target.value)} />
            </Field>
            <Field label="Systolic BP">
              <input type="number" className={inputClass} value={form.sbp}
                onChange={(e) => update("sbp", e.target.value)} />
            </Field>
            <Field label="Diastolic BP">
              <input type="number" className={inputClass} value={form.dbp}
                onChange={(e) => update("dbp", e.target.value)} />
            </Field>
            <Field label="Resp. rate (/min)">
              <input type="number" className={inputClass} value={form.resprate}
                onChange={(e) => update("resprate", e.target.value)} />
            </Field>
            <Field label="SpO2 (%)">
              <input type="number" min="0" max="100" className={inputClass} value={form.o2sat}
                onChange={(e) => update("o2sat", e.target.value)} />
            </Field>
            <Field label="Temperature">
              <input type="number" step="0.1" className={inputClass} value={form.temperature}
                onChange={(e) => update("temperature", e.target.value)} />
            </Field>
            <Field label="Pain (0-10)">
              <input type="number" min="0" max="10" className={inputClass} value={form.pain}
                onChange={(e) => update("pain", e.target.value)} />
            </Field>
          </div>
        </div>

        <div className="panel p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Chief complaint & findings</h2>
          <div className="mt-4">
            <Field label="Chief complaint">
              <input type="text" className={inputClass} value={form.chief_complaint}
                onChange={(e) => update("chief_complaint", e.target.value)} placeholder="e.g. Chest discomfort" />
            </Field>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {FINDING_FIELDS.map(([key, label]) => (
              <label key={key} className="flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" checked={form[key]} onChange={(e) => update(key, e.target.checked)}
                  className="rounded border-surface-border" />
                {label}
              </label>
            ))}
          </div>
        </div>

        <button type="submit" disabled={submitting}
          className="btn-primary w-full">
          {submitting ? "Submitting…" : "Submit triage assessment"}
        </button>

        {error && <div className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-600">{error}</div>}
      </form>

      <div className="lg:sticky lg:top-6 lg:self-start">
        <div className="panel p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
              {submitted ? "Submitted recommendation" : "Live AI preview"}
            </h2>
            {previewLoading && !submitted && <span className="text-xs text-accent-mintInk">scoring…</span>}
          </div>

          {!displayed && (
            <p className="mt-4 text-sm text-surface-muted">Enter at least one vital sign or chief complaint to see a live AI preview.</p>
          )}

          {displayed && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <PriorityBadge priority={displayed.priority} />
                {displayed.escalated && <span className="text-xs font-medium text-red-500">⚠ Escalated</span>}
              </div>
              <div className="flex justify-center">
                <ConfidenceGauge confidence={displayed.confidence} size={140} />
              </div>
              <p className="text-center text-sm text-slate-600">
                Risk score <span className="font-bold text-surface-ink">{displayed.risk_score}</span>/100
              </p>
              {displayed.uncertainty_reason && (
                <p className="rounded-lg bg-white px-3 py-2 text-xs text-surface-muted">
                  {displayed.uncertainty_reason}
                </p>
              )}
              <ul className="space-y-1 text-xs text-slate-600">
                {displayed.top_features.map((f, i) => (
                  <li key={i}>• {f}</li>
                ))}
              </ul>
              <p className="border-t border-surface-border pt-3 text-center text-xs font-medium text-surface-muted">
                {displayed.governing_rule}
              </p>
            </motion.div>
          )}
          {/* Sepsis alert — only on final submit, not live preview */}
          {submitted?.sepsis_alert && (
            <div className="mt-4">
              <SepsisAlert
                result={submitted}
                onAcknowledge={(info) => console.info("Sepsis ack:", info)}
              />
            </div>
          )}

          {/* Re-open protocol modal */}
          {submitted?.triggered_protocols?.length > 0 && !showProtocols && (
            <button
              onClick={() => setShowProtocols(true)}
              className="mt-4 w-full rounded-xl border border-red-200 bg-red-50 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-100"
            >
              {submitted.triggered_protocols[0].icon} Re-open{" "}
              {submitted.triggered_protocols.map((p) => p.title).join(" + ")} Protocol
            </button>
          )}
        </div>
      </div>
    </div>
    </>
  );
}
