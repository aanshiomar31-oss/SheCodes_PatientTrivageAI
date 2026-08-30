import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const DEPLOYMENT_MODES = [
  {
    id: "basic",
    name: "Basic Station",
    icon: "💻",
    desc: "Single workstation local installation. Fully offline capable with SQLite backend. Data stays on-device.",
    architecture: ["Workstation", "Local Database"],
  },
  {
    id: "connected",
    name: "Connected Enterprise",
    icon: "🌐",
    desc: "Intra-hospital network connection. Shared triage database and WebSockets supporting multiple nurses and doctors simultaneously.",
    architecture: ["Triage Desk 1", "Triage Desk 2", "Doctor Console", "Shared Server DB"],
  },
  {
    id: "advanced",
    name: "Cloud Command Hub",
    icon: "☁️",
    desc: "Regional cloud architecture coordinate. Enables inter-hospital referrals, capacity maps, and load balancing across nodes.",
    architecture: ["Cloud Gateway", "Rural Clinic", "District Gen", "Trauma Hub", "Global Analytics"],
  },
];

export default function DeploymentMode() {
  const [selectedMode, setSelectedMode] = useState("connected");

  const activeMode = DEPLOYMENT_MODES.find(m => m.id === selectedMode);

  return (
    <div className="panel p-5 space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-3 border-b border-surface-border pb-3">
        <div>
          <h3 className="label">Federated Deployment Architectures</h3>
          <p className="text-xs text-surface-muted mt-1">Scale PatientTriage.ai across single nodes or regional clouds.</p>
        </div>

        {/* Segmented control selector */}
        <div className="flex bg-accent-wash rounded-xl border border-surface-border p-1">
          {DEPLOYMENT_MODES.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setSelectedMode(mode.id)}
              className={`px-3 py-1.5 text-[10px] font-bold uppercase rounded-lg transition ${
                selectedMode === mode.id
                  ? "bg-accent-blue text-white shadow-sm"
                  : "text-surface-muted hover:text-white"
              }`}
            >
              {mode.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Detail Panel */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{activeMode.icon}</span>
            <div>
              <h4 className="text-sm font-bold text-white">{activeMode.name} Setup</h4>
              <p className="text-xs text-accent-mint font-semibold">Triage Scale Target</p>
            </div>
          </div>
          <p className="text-xs text-surface-muted leading-relaxed">{activeMode.desc}</p>
        </div>

        {/* Animated Architecture Visualizer */}
        <div className="h-44 relative bg-[#091510] border border-surface-border rounded-xl flex items-center justify-center overflow-hidden p-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={selectedMode}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-wrap gap-3 justify-center items-center max-w-xs"
            >
              {activeMode.architecture.map((node, idx) => (
                <div
                  key={node}
                  className="flex flex-col items-center"
                >
                  <motion.div
                    initial={{ y: 5 }}
                    animate={{ y: [0, -5, 0] }}
                    transition={{ repeat: Infinity, duration: 2.5, delay: idx * 0.3 }}
                    className="h-10 px-3 flex items-center justify-center rounded-xl bg-surface-panel border border-accent-mint/30 shadow-sm"
                  >
                    <span className="text-[10px] font-bold text-accent-mint whitespace-nowrap">{node}</span>
                  </motion.div>
                  {idx < activeMode.architecture.length - 1 && (
                    <span className="text-[10px] text-surface-muted font-bold rotate-90 md:rotate-0">⇆</span>
                  )}
                </div>
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
