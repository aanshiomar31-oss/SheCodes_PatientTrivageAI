import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  fetchFeatureImportance,
  fetchModelStatus,
  fetchTriageStays,
  fetchTriageStaysSummary,
  scoreAllStays,
} from "../services/api.js";
import AcuityChart from "../components/AcuityChart.jsx";
import TriageStayTable from "../components/TriageStayTable.jsx";

const ACUITY_FILTERS = [
  { value: "", label: "All acuity" },
  { value: "1", label: "1 · Critical" },
  { value: "2", label: "2 · Urgent" },
  { value: "3", label: "3 · Moderate" },
  { value: "4", label: "4 · Low" },
  { value: "5", label: "5 · Non-urgent" },
];

function Card({ children, className = "" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`panel p-6 ${className}`}
    >
      {children}
    </motion.div>
  );
}

function StatTile({ label, value, sub }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-surface-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-surface-ink">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-surface-muted">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [summaryError, setSummaryError] = useState(null);

  const [modelStatus, setModelStatus] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [scoreMessage, setScoreMessage] = useState(null);

  const [featureImportance, setFeatureImportance] = useState(null);

  const [stays, setStays] = useState(null);
  const [staysLoading, setStaysLoading] = useState(true);
  const [acuityFilter, setAcuityFilter] = useState("");
  const [highRiskOnly, setHighRiskOnly] = useState(false);

  // Load summary + model status independently — each panel shows its
  // own loading/error state rather than one blocking fetch gating the
  // whole page (see file_creation_advice: display data progressively).
  useEffect(() => {
    let cancelled = false;
    fetchTriageStaysSummary()
      .then((data) => !cancelled && setSummary(data))
      .catch((err) => !cancelled && setSummaryError(err.response?.status === 404 ? "no-data" : "error"));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchModelStatus()
      .then((data) => !cancelled && setModelStatus(data))
      .catch(() => !cancelled && setModelStatus({ available: false }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (modelStatus?.available) {
      fetchFeatureImportance()
        .then(setFeatureImportance)
        .catch(() => setFeatureImportance(null));
    }
  }, [modelStatus]);

  useEffect(() => {
    let cancelled = false;
    setStaysLoading(true);
    fetchTriageStays({
      limit: 100,
      acuity: acuityFilter || undefined,
      highRiskOnly: highRiskOnly || undefined,
    })
      .then((data) => !cancelled && setStays(data.items))
      .catch(() => !cancelled && setStays([]))
      .finally(() => !cancelled && setStaysLoading(false));
    return () => {
      cancelled = true;
    };
  }, [acuityFilter, highRiskOnly]);

  async function handleScoreAll() {
    setScoring(true);
    setScoreMessage(null);
    try {
      const result = await scoreAllStays();
      setScoreMessage(`Scored ${result.scored} stays (${result.skipped_already_scored} already up to date).`);
      const [freshSummary, freshStays] = await Promise.all([
        fetchTriageStaysSummary(),
        fetchTriageStays({ limit: 100, acuity: acuityFilter || undefined, highRiskOnly: highRiskOnly || undefined }),
      ]);
      setSummary(freshSummary);
      setStays(freshStays.items);
    } catch (err) {
      setScoreMessage(err.response?.data?.detail || "Scoring failed — is a model trained? Run `python -m ml.train`.");
    } finally {
      setScoring(false);
    }
  }

  return (
    <div className="space-y-6">
      {summaryError === "no-data" && (
        <Card>
          <h3 className="text-sm font-semibold text-surface-ink">No triage data loaded yet</h3>
          <p className="mt-2 text-sm text-slate-600">
            Run the following from <code className="rounded bg-slate-100 px-1.5 py-0.5">backend/</code>:
          </p>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-white px-4 py-3 text-xs text-surface-ink">
            {"python -m alembic upgrade head\npython load_triage_stays.py\npython -m ml.train"}
          </pre>
        </Card>
      )}

      {summaryError === "error" && (
        <Card>
          <p className="text-sm text-red-700">Could not reach the backend API. Make sure it&apos;s running (see README.md).</p>
        </Card>
      )}

      {/* Cohort overview */}
      {summary && (
        <Card>
          <h2 className="text-lg font-semibold text-surface-ink">Cohort overview</h2>
          <p className="mt-1 text-sm text-surface-muted">
            MIMIC-IV-ED (Demo) — {summary.total_stays} ED stays loaded from <code>triage_stays</code>.
          </p>
          <div className="mt-5 grid grid-cols-2 gap-6 sm:grid-cols-4">
            <StatTile label="Total stays" value={summary.total_stays} />
            <StatTile label="Untriaged" value={summary.untriaged_count} sub="no matching acuity record" />
            <StatTile label="Zero vitals" value={summary.zero_vitals_count} sub="6+ vitals missing — not 'well'" />
            <StatTile
              label="Model-flagged"
              value={summary.scored_count > 0 ? summary.predicted_high_acuity_count : "—"}
              sub={summary.scored_count > 0 ? `of ${summary.scored_count} scored` : "not scored yet"}
            />
          </div>

          <div className="mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-surface-muted">Acuity distribution</h3>
            <div className="mt-2">
              <AcuityChart acuityCounts={summary.acuity_counts} />
            </div>
          </div>

          {summary.data_quality_notes?.length > 0 && (
            <div className="mt-6 rounded-lg bg-amber-50 px-4 py-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-800">Data quality notes</h3>
              <ul className="mt-2 space-y-1.5 text-sm text-amber-800">
                {summary.data_quality_notes.map((note, i) => (
                  <li key={i} className="flex gap-2">
                    <span aria-hidden="true">•</span>
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Model panel */}
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-surface-ink">Model</h2>
            {modelStatus === null && <p className="mt-1 text-sm text-surface-muted">Checking model status…</p>}
            {modelStatus && !modelStatus.available && (
              <p className="mt-1 text-sm text-slate-600">
                No trained model found. Run{" "}
                <code className="rounded bg-slate-100 px-1.5 py-0.5">python -m ml.train</code> from{" "}
                <code className="rounded bg-slate-100 px-1.5 py-0.5">backend/</code>.
              </p>
            )}
            {modelStatus?.available && (
              <p className="mt-1 text-sm text-slate-600">
                <span className="font-medium text-surface-ink">{modelStatus.version}</span> · threshold{" "}
                {modelStatus.threshold} · {modelStatus.feature_count} features
              </p>
            )}
          </div>
          {modelStatus?.available && (
            <button
              onClick={handleScoreAll}
              disabled={scoring}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-surface-ink hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {scoring ? "Scoring…" : "Score all stays"}
            </button>
          )}
        </div>

        {scoreMessage && <p className="mt-3 text-sm text-slate-600">{scoreMessage}</p>}

        {featureImportance?.feature_importance?.length > 0 && (
          <div className="mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-surface-muted">
              Top features ({featureImportance.method === "shap" ? "SHAP" : "permutation importance"})
            </h3>
            <ul className="mt-2 space-y-1.5">
              {featureImportance.feature_importance.slice(0, 8).map(([name, value]) => (
                <li key={name} className="flex items-center gap-3">
                  <span className="w-44 shrink-0 truncate text-sm text-slate-600">{name}</span>
                  <div className="h-2 flex-1 rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-blue-500"
                      style={{
                        width: `${Math.min(
                          100,
                          (value / featureImportance.feature_importance[0][1]) * 100
                        )}%`,
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {/* Stay table */}
      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-surface-ink">ED stays</h2>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={acuityFilter}
              onChange={(e) => setAcuityFilter(e.target.value)}
              className="rounded-lg border border-surface-border bg-white px-3 py-1.5 text-sm text-slate-600"
            >
              {ACUITY_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={highRiskOnly}
                onChange={(e) => setHighRiskOnly(e.target.checked)}
                className="rounded border-surface-border"
              />
              Model-flagged only
            </label>
          </div>
        </div>
        <TriageStayTable stays={stays} loading={staysLoading} />
      </div>
    </div>
  );
}
