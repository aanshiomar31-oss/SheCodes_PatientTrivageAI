import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useLiveSocket } from "../hooks/useLiveSocket.js";
import { useDemo } from "../context/DemoContext.jsx";

const NAV_LINKS = [
  { to: "/", label: "Command Center", icon: "📊", end: true },
  { to: "/intake", label: "Patient Intake", icon: "📋" },
  { to: "/queue", label: "Live Queue", icon: "⏳" },
  { to: "/comparison", label: "Comparison", icon: "🔄" },
  { to: "/explainability", label: "Explainability", icon: "💡" },
  { to: "/trust-center", label: "Trust Center", icon: "🛡️" },
  { to: "/security", label: "Security Dashboard", icon: "🔒" },
  { to: "/hospital-network", label: "Hospital Network", icon: "🏥" },
  { to: "/audit", label: "Audit Logs", icon: "📜" },
  { to: "/digital-twin", label: "Digital Twin", icon: "👥" },
];

export default function Layout({ children }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [tickerMessage, setTickerMessage] = useState("Monitoring patient arrivals...");
  const { demo, setDemo } = useDemo();
  const location = useLocation();

  // Listen to live events to update the top activity ticker
  useLiveSocket({
    new_patient: (e) => {
      setTickerMessage(`🚨 New Intake: Patient ${e.patient_id} assigned recommended priority ${e.priority}`);
    },
    override: (e) => {
      setTickerMessage(`✍️ Priority Override: Stay #${e.stay_id} updated (${e.original_priority} → ${e.new_priority})`);
    },
    vitals_updated: (e) => {
      setTickerMessage(`🩺 Vitals Update: Stay #${e.stay_id} vitals refreshed`);
    },
    retriage_breach: (e) => {
      setTickerMessage(`⚠️ Breach Warning: Patient ${e.patient_id} has exceeded wait threshold`);
    }
  });

  return (
    <div className="flex min-h-screen bg-surface-bg text-surface-ink font-sans antialiased">
      {/* Collapsible Sidebar */}
      <motion.aside
        animate={{ width: isExpanded ? 260 : 78 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="sticky top-0 left-0 flex h-screen flex-col border-r border-surface-border bg-white shadow-sm z-40 shrink-0 overflow-hidden"
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-surface-border">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-mint text-sm font-bold text-white shadow-sm">
              P
            </div>
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="whitespace-nowrap"
              >
                <h1 className="text-sm font-bold leading-tight text-surface-ink">PatientTriage.ai</h1>
                <p className="text-[10px] leading-tight text-surface-muted">ED Command Center</p>
              </motion.div>
            )}
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-slate-100 transition text-slate-500"
            aria-label={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
          >
            {isExpanded ? "◀" : "▶"}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 space-y-1.5 p-3 overflow-y-auto">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all duration-250 focus:outline-none ${
                  isActive
                    ? "bg-accent-wash text-accent-mintInk shadow-sm scale-102"
                    : "text-slate-600 hover:bg-slate-50 hover:text-surface-ink hover:translate-x-1"
                }`
              }
            >
              <span className="text-lg shrink-0">{link.icon}</span>
              {isExpanded && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="whitespace-nowrap"
                >
                  {link.label}
                </motion.span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer info/tagline */}
        <div className="border-t border-surface-border p-4 bg-slate-50/50">
          {isExpanded ? (
            <p className="text-[10px] font-semibold text-accent-mintInk leading-relaxed text-center">
              The AI recommends. <br />The nurse decides.
            </p>
          ) : (
            <div className="text-center text-sm font-bold text-accent-mintInk">🩺</div>
          )}
        </div>
      </motion.aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-surface-border bg-white/70 backdrop-blur-md px-6">
          {/* Live scrolling / switching activity ticker */}
          <div className="flex items-center gap-2 overflow-hidden max-w-lg">
            <span className="relative flex h-2 w-2 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-mint opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-mint"></span>
            </span>
            <AnimatePresence mode="wait">
              <motion.p
                key={tickerMessage}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-xs font-semibold text-slate-600 whitespace-nowrap overflow-hidden text-ellipsis"
              >
                {tickerMessage}
              </motion.p>
            </AnimatePresence>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Global Demo Mode Toggle Switch */}
            <div className="flex items-center gap-2 bg-slate-50 border border-surface-border rounded-full px-3 py-1.5 shadow-sm">
              <span className="text-xs font-bold text-slate-500">Demo Mode</span>
              <button
                onClick={() => setDemo(!demo)}
                className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  demo ? "bg-accent-mint" : "bg-slate-200"
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    demo ? "translate-x-4" : "translate-x-0"
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <span className="text-accent-mint">●</span> Live Server Connected
            </div>
          </div>
        </header>

        {/* Dynamic page contents with Framer Motion entry animation */}
        <main className="flex-grow p-6 md:p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="border-t border-surface-border bg-white px-6 py-4 text-center text-[10px] text-surface-muted">
          PatientTriage.ai — rule engine + stacking ensemble + SHAP explainability, live over WebSocket.
        </footer>
      </div>
    </div>
  );
}
