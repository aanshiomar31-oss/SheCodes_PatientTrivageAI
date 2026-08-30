import { useEffect, useState } from "react";
import { fetchFeatureImportance, fetchQueue, submitTriage, fetchTriageStay } from "../services/api.js";
import SHAPPanel from "../components/SHAPPanel.jsx";
import ConfidenceGauge from "../components/ConfidenceGauge.jsx";
import PriorityBadge from "../components/PriorityBadge.jsx";

export default function Explainability() {
  const [globalImportance, setGlobalImportance] = useState(null);
  const [globalError, setGlobalError] = useState(null);

  const [queueEntries, setQueueEntries] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [patientResult, setPatientResult] = useState(null);
  const [loadingPatient, setLoadingPatient] = useState(false);

  useEffect(() => {
    fetchFeatureImportance()
      .then((data) => setGlobalImportance(data.feature_importance))
      .catch(() => setGlobalError("No trained model / feature importance available yet. Run `python -m ml.explain`."));
    fetchQueue("arrival").then((data) => setQueueEntries(data.entries)).catch(() => {});
  }, []);

  async function explainPatient(stayId) {
    setSelectedId(stayId);
    setLoadingPatient(true);
    setPatientResult(null);
    try {
      const stay = await fetchTriageStay(stayId);
      const rec = await submitTriage({
        age: null, gender: stay.gender, heartrate: stay.heart_rate, sbp: stay.sbp, dbp: stay.dbp,
        resprate: stay.resp_rate, temperature: stay.temperature, o2sat: stay.o2_sat, pain: stay.pain,
        chief_complaint: stay.chief_complaint,
      });
      setPatientResult(rec);
    } catch {
      setPatientResult(null);
    } finally {
      setLoadingPatient(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-ink">Explainability</h1>
        <p className="text-sm text-surface-muted">Global model behavior, and why the AI recommended what it did for one patient.</p>
      </div>

      <div className="panel p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">
          Global feature importance <span className="text-surface-muted">(real SHAP magnitudes from training)</span>
        </h2>
        <div className="mt-4">
          {globalError && <p className="text-sm text-surface-muted">{globalError}</p>}
          {globalImportance && <SHAPPanel mode="global" data={globalImportance} />}
        </div>
      </div>

      <div className="panel p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-600">Explain one patient</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {queueEntries.slice(0, 24).map((e) => (
            <button
              key={e.stay_id}
              onClick={() => explainPatient(e.stay_id)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                selectedId === e.stay_id
                  ? "border-accent-mint bg-accent-wash text-accent-mintInk"
                  : "border-surface-border text-surface-muted hover:bg-slate-50"
              }`}
            >
              #{e.stay_id}
            </button>
          ))}
        </div>

        {loadingPatient && <p className="mt-4 text-sm text-surface-muted">Scoring…</p>}

        {patientResult && (
          <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="flex flex-col items-center gap-3">
              <PriorityBadge priority={patientResult.priority} />
              <ConfidenceGauge confidence={patientResult.confidence} />
              {patientResult.uncertainty_reason && (
                <p className="text-center text-xs text-surface-muted">{patientResult.uncertainty_reason}</p>
              )}
            </div>
            <div className="md:col-span-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-surface-muted">
                Ranked contributing factors <span className="text-slate-600">(ordinal, not numeric SHAP)</span>
              </h3>
              <div className="mt-3">
                <SHAPPanel mode="patient" data={patientResult.top_features} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
