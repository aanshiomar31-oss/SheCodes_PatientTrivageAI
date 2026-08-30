import { motion } from "framer-motion";

const COMPLIANCE_ITEMS = [
  {
    name: "HIPAA Compliant",
    status: "Active",
    desc: "Health Insurance Portability and Accountability Act. Enforces strict protected health information (PHI) protection controls.",
    icon: "🇺🇸",
  },
  {
    name: "GDPR Certified",
    status: "Active",
    desc: "General Data Protection Regulation. Guarantees patient right-to-be-forgotten and data portability safeguards.",
    icon: "🇪🇺",
  },
  {
    name: "ABDM Ready",
    status: "Active",
    desc: "Ayushman Bharat Digital Mission. Supports secure unified Health ID integration and consent-based health data exchange.",
    icon: "🇮🇳",
  },
];

export default function ComplianceBadges() {
  return (
    <div className="panel p-5 space-y-4">
      <div>
        <h3 className="label">Compliance & Regulatory Standards</h3>
        <p className="text-xs text-surface-muted mt-1">Verification credentials and healthcare data frameworks.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {COMPLIANCE_ITEMS.map((item, idx) => (
          <motion.div
            key={item.name}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            className="flex items-start gap-3 p-4 bg-accent-wash/30 border border-surface-border rounded-xl"
          >
            <span className="text-2xl mt-1">{item.icon}</span>
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-white">{item.name}</h4>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-accent-wash text-accent-mint border border-accent-mint/20">
                  {item.status}
                </span>
              </div>
              <p className="text-[11px] text-surface-muted leading-relaxed">{item.desc}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
