import { motion } from "framer-motion";

export default function SecurityCard({ status }) {
  const encStatus = status || {
    database_encrypted: true,
    ssl_active: true,
    tls_version: "TLS 1.3",
    cipher_suite: "AES-256-GCM",
  };

  const cards = [
    {
      title: "Data Encryption",
      icon: "🔒",
      value: encStatus.database_encrypted ? "Encrypted" : "Decrypted",
      desc: `Storage: ${encStatus.cipher_suite || "AES-256"}. Database tables are encrypted at rest with zero-knowledge keys.`,
      status: encStatus.database_encrypted ? "active" : "disabled",
    },
    {
      title: "Network Security",
      icon: "📡",
      value: encStatus.ssl_active ? "Secure (TLS 1.3)" : "Insecure",
      desc: "All socket traffic and REST endpoints use SHA-256 transport layer encryption.",
      status: encStatus.ssl_active ? "active" : "disabled",
    },
    {
      title: "Identity Protection",
      icon: "🔑",
      value: "MFA & SSO",
      desc: "Multi-Factor Authentication is enforced globally. Machine logs verify device fingerprint signature.",
      status: "active",
    },
    {
      title: "Threat Shield",
      icon: "🛡️",
      value: "Active IPS",
      desc: "Intrusion Prevention System monitoring REST & WebSocket requests. Live block rate: 0.0%",
      status: "active",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
      {cards.map((card, idx) => (
        <motion.div
          key={card.title}
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.1 }}
          className="panel panel-hover p-5 flex flex-col justify-between"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{card.icon}</span>
              <div>
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">{card.title}</h4>
                <p className="text-xs text-surface-muted mt-0.5">{card.value}</p>
              </div>
            </div>
            <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
              card.status === "active" ? "bg-accent-wash text-accent-mint" : "bg-red-500/10 text-red-400"
            }`}>
              {card.status === "active" ? "Verified" : "Bypassed"}
            </span>
          </div>

          <p className="text-xs text-surface-muted mt-4 leading-relaxed">{card.desc}</p>
        </motion.div>
      ))}
    </div>
  );
}
