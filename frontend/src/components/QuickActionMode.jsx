import { useState, useRef, useEffect } from "react";
import { submitTriage } from "../services/api.js";
import PriorityBadge from "./PriorityBadge.jsx";
import { motion, AnimatePresence } from "framer-motion";

const SYMPTOM_CHIPS = [
  { label: "Chest Pain", complaint: "Acute chest pain, pressure, and radiating arm pain", payload: { chest_pain: true, diaphoresis: true, sbp: 140, dbp: 90, heartrate: 96 } },
  { label: "Stroke", complaint: "Sudden facial droop, slurred speech, right arm weakness", payload: { fast_positive: true, sbp: 160, dbp: 95 } },
  { label: "Fever", complaint: "High fever, chills, lethargy", payload: { temperature: 101.5, heartrate: 105 } },
  { label: "Trauma", complaint: "Motor vehicle crash, open fracture, severe pain", payload: { pain: 9, heartrate: 110, sbp: 115, dbp: 75 } },
  { label: "Short of Breath", complaint: "Acute dyspnea, accessory muscle use, tachypnea", payload: { resprate: 28, o2sat: 90 } },
  { label: "Unresponsive", complaint: "Found unresponsive, breathing but does not follow commands", payload: { unresponsive: true, heartrate: 58, sbp: 90, dbp: 50, o2sat: 92, resprate: 10 } },
];

export default function QuickActionMode() {
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [complaint, setComplaint] = useState("");
  const [vitals, setVitals] = useState({ heartrate: "", sbp: "", dbp: "", resprate: "", o2sat: "", temperature: "", pain: "" });
  const [findings, setFindings] = useState({ chest_pain: false, diaphoresis: false, fast_positive: false, unresponsive: false, seizing: false, airway_compromise: false, stridor: false });
  const [activeChip, setActiveChip] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const ageInputRef = useRef(null);

  // Auto-focus age input when Quick Action Mode is loaded
  useEffect(() => {
    if (ageInputRef.current) {
      ageInputRef.current.focus();
    }
  }, []);

  const selectChip = (chip) => {
    setActiveChip(chip.label);
    setComplaint(chip.complaint);
    
    // Clear and overwrite vitals & findings with chip payloads
    const newVitals = { heartrate: "", sbp: "", dbp: "", resprate: "", o2sat: "", temperature: "", pain: "" };
    Object.keys(chip.payload).forEach(k => {
      if (k in newVitals) newVitals[k] = chip.payload[k];
    });
    setVitals(newVitals);

    const newFindings = { chest_pain: false, diaphoresis: false, fast_positive: false, unresponsive: false, seizing: false, airway_compromise: false, stridor: false };
    Object.keys(chip.payload).forEach(k => {
      if (k in newFindings) newFindings[k] = chip.payload[k];
    });
    setFindings(newFindings);
  };

  const handleIntakeSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    // Build payload
    const payload = {
      age: age ? Number(age) : null,
      gender: gender || null,
      chief_complaint: complaint || null,
      ...findings
    };

    Object.keys(vitals).forEach(k => {
      payload[k] = vitals[k] !== "" ? Number(vitals[k]) : null;
    });

    try {
      const data = await submitTriage(payload);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Quick intake triage failed. Please verify inputs.");
    } finally {
      setLoading(false);
    }
  };

  const clearForm = () => {
    setAge("");
    setGender("");
    setComplaint("");
    setVitals({ heartrate: "", sbp: "", dbp: "", resprate: "", o2sat: "", temperature: "", pain: "" });
    setFindings({ chest_pain: false, diaphoresis: false, fast_positive: false, unresponsive: false, seizing: false, airway_compromise: false, stridor: false });
    setActiveChip(null);
    setResult(null);
    setError(null);
    if (ageInputRef.current) ageInputRef.current.focus();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 panel p-6 space-y-6">
        <div>
          <h3 className="label">Quick Action Emergency Intake</h3>
          <p className="text-xs text-surface-muted mt-1">Designed for high-pressure situations. Complete clinical triage under 30 seconds.</p>
        </div>

        {/* 1-Click Symptom Chips */}
        <div>
          <span className="text-xs font-bold text-surface-muted block mb-2">Select Critical Presentation</span>
          <div className="flex flex-wrap gap-2">
            {SYMPTOM_CHIPS.map((chip) => (
              <button
                key={chip.label}
                type="button"
                onClick={() => selectChip(chip)}
                className={`px-4 py-3 rounded-xl text-xs font-bold transition-all ${
                  activeChip === chip.label
                    ? "bg-accent-blue text-white shadow-lift border border-accent-blue"
                    : "bg-accent-wash text-surface-muted hover:text-white border border-surface-border"
                }`}
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleIntakeSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-surface-muted">Age (Years)</label>
              <input
                type="number"
                inputMode="numeric"
                pattern="[0-9]*"
                ref={ageInputRef}
                value={age}
                onChange={e => setAge(e.target.value)}
                placeholder="Age"
                className="input h-12 text-lg font-bold mt-1"
                required
              />
            </div>
            <div>
              <label className="text-xs font-bold text-surface-muted">Gender</label>
              <select
                value={gender}
                onChange={e => setGender(e.target.value)}
                className="input h-12 text-base font-bold mt-1"
              >
                <option value="">Select</option>
                <option value="M">Male (M)</option>
                <option value="F">Female (F)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className="text-[11px] font-bold text-surface-muted">HR (bpm)</label>
              <input
                type="number"
                inputMode="numeric"
                value={vitals.heartrate}
                onChange={e => setVitals({...vitals, heartrate: e.target.value})}
                placeholder="HR"
                className="input h-10 mt-1"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-surface-muted">BP (Systolic)</label>
              <input
                type="number"
                inputMode="numeric"
                value={vitals.sbp}
                onChange={e => setVitals({...vitals, sbp: e.target.value})}
                placeholder="SBP"
                className="input h-10 mt-1"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-surface-muted">SpO2 (%)</label>
              <input
                type="number"
                inputMode="numeric"
                value={vitals.o2sat}
                onChange={e => setVitals({...vitals, o2sat: e.target.value})}
                placeholder="SpO2"
                className="input h-10 mt-1"
              />
            </div>
            <div>
              <label className="text-[11px] font-bold text-surface-muted">Pain (0-10)</label>
              <input
                type="number"
                inputMode="numeric"
                value={vitals.pain}
                onChange={e => setVitals({...vitals, pain: e.target.value})}
                placeholder="Pain"
                className="input h-10 mt-1"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-surface-muted">Chief Complaint</label>
            <input
              type="text"
              value={complaint}
              onChange={e => setComplaint(e.target.value)}
              placeholder="Enter complaint..."
              className="input h-12 mt-1"
              required
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex-1 h-14 text-base font-bold shadow-lift flex items-center justify-center"
            >
              {loading ? "Intaking..." : "⚡ Quick Triage"}
            </button>
            <button
              type="button"
              onClick={clearForm}
              className="btn-ghost px-6 h-14 font-bold"
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      {/* Response Panel */}
      <div className="panel p-6 flex flex-col justify-between">
        <div>
          <h3 className="label">Live Triage Response</h3>
          <p className="text-xs text-surface-muted mt-1">Instant scoring feedback from rules & ensemble models.</p>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center py-6 min-h-[250px]">
          <AnimatePresence mode="wait">
            {error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-red-400 space-y-2">
                <span className="text-3xl">⚠️</span>
                <p className="text-sm font-bold">{error}</p>
              </motion.div>
            )}

            {!error && !result && !loading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-surface-muted space-y-2">
                <span className="text-4xl">⏱️</span>
                <p className="text-xs">Fill the form or tap a symptom chip to execute quick assessment.</p>
              </motion.div>
            )}

            {loading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-accent-mint space-y-2">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-accent-mint mx-auto"></div>
                <p className="text-xs mt-2">Computing priority floor...</p>
              </motion.div>
            )}

            {!error && result && !loading && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center space-y-4 w-full"
              >
                <div className="flex justify-center">
                  <PriorityBadge priority={result.priority} />
                </div>
                <div>
                  <p className="text-sm text-surface-muted">Recommended Acuity Level</p>
                  <p className="text-3xl font-extrabold text-surface-ink mt-1">{result.risk_score}% Risk</p>
                  <p className="text-xs text-surface-muted mt-0.5">Clinical Priority Score: {result.clinical_priority_score}</p>
                </div>
                {result.triggered_protocols?.length > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-left">
                    <span className="text-[10px] font-bold uppercase text-red-800 block mb-1">Triggered Protocols</span>
                    {result.triggered_protocols.map((p, i) => (
                      <span key={i} className="text-xs text-red-700 block">• {p.title || p.code} Protocol</span>
                    ))}
                  </div>
                )}
                {result.sepsis_alert && (
                  <div className="bg-orange-50 border border-orange-200 rounded-xl p-3 text-left text-orange-700 text-xs">
                    ⚠️ Sepsis Screen Positive: {result.sepsis_message}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="border-t border-surface-border pt-4 text-center">
          <p className="text-[10px] text-surface-muted">
            Intake submissions instantly join the active Live Queue via WebSockets.
          </p>
        </div>
      </div>
    </div>
  );
}
