import { useState, useEffect } from "react";
import { fetchQueue } from "../services/api.js";
import AIConfidenceCard from "../components/AIConfidenceCard.jsx";
import OverrideAnalytics from "../components/OverrideAnalytics.jsx";
import QuickActionMode from "../components/QuickActionMode.jsx";
import TrustTimeline from "../components/TrustTimeline.jsx";
import TrainingPanel from "../components/TrainingPanel.jsx";
import { motion } from "framer-motion";

export default function TrustCenter() {
  const [activeTab, setActiveTab] = useState("decision");
  const [queue, setQueue] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadQueueData = async () => {
    setLoading(true);
    try {
      const data = await fetchQueue("priority");
      const entries = data?.entries ?? [];
      setQueue(entries);
      if (entries.length > 0 && !selectedPatient) {
        setSelectedPatient(entries[0]);
      }
    } catch (err) {
      console.error("Error loading queue in TrustCenter:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "decision") {
      loadQueueData();
    }
  }, [activeTab]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            🛡️ Clinical Trust & Adoption Center
          </h1>
          <p className="text-sm text-surface-muted">
            Auditing decision accuracy, override logs, and onboarding training.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex bg-accent-wash rounded-xl border border-surface-border p-1">
          <button
            onClick={() => setActiveTab("decision")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition ${
              activeTab === "decision" ? "bg-accent-blue text-white shadow-sm" : "text-surface-muted hover:text-white"
            }`}
          >
            Decision Trust
          </button>
          <button
            onClick={() => setActiveTab("analytics")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition ${
              activeTab === "analytics" ? "bg-accent-blue text-white shadow-sm" : "text-surface-muted hover:text-white"
            }`}
          >
            Override Analytics
          </button>
          <button
            onClick={() => setActiveTab("quick-action")}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition ${
              activeTab === "quick-action" ? "bg-accent-blue text-white shadow-sm" : "text-surface-muted hover:text-white"
            }`}
          >
            Quick Intake Mode
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="mt-4">
        {activeTab === "decision" && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Sidebar Patient selector */}
            <div className="panel p-5 space-y-4">
              <div>
                <h3 className="label">Active Queue Selection</h3>
                <p className="text-xs text-surface-muted mt-1">Select an active stay to audit factors & decision timelines.</p>
              </div>

              {loading ? (
                <div className="py-12 text-center text-accent-mint font-semibold text-xs">Loading queue stays...</div>
              ) : queue.length === 0 ? (
                <div className="py-12 text-center text-surface-muted text-xs">No active triage patients in queue.</div>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                  {queue.map((pt) => (
                    <button
                      key={pt.stay_id}
                      onClick={() => setSelectedPatient(pt)}
                      className={`w-full text-left p-3 rounded-xl border transition ${
                        selectedPatient?.stay_id === pt.stay_id
                          ? "bg-accent-wash border-accent-mint/30"
                          : "border-surface-border bg-surface-bg/10 hover:bg-surface-bg/30"
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-white">Stay #{pt.stay_id}</span>
                        <span className="text-[10px] text-surface-muted">{pt.patient_id}</span>
                      </div>
                      <p className="text-[11px] text-surface-muted truncate mt-1">{pt.chief_complaint || "No complaint text"}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* AI confidence & timeline inspect */}
            <div className="xl:col-span-2 space-y-6">
              <AIConfidenceCard patient={selectedPatient} />
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <TrustTimeline patient={selectedPatient} />
                <TrainingPanel />
              </div>
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <OverrideAnalytics />
          </motion.div>
        )}

        {activeTab === "quick-action" && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <QuickActionMode />
          </motion.div>
        )}
      </div>
    </div>
  );
}
