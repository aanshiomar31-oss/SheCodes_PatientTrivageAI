import { useState, useEffect } from "react";
import { fetchSecurityStatus, fetchSecurityAudit } from "../services/api.js";
import SecurityCard from "../components/SecurityCard.jsx";
import PermissionMatrix from "../components/PermissionMatrix.jsx";
import AuditTimeline from "../components/AuditTimeline.jsx";
import ComplianceBadges from "../components/ComplianceBadges.jsx";
import { motion } from "framer-motion";

export default function Security() {
  const [status, setStatus] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [toggles, setToggles] = useState({
    autoLogout: true,
    sessionTimeout: true,
    deviceVerification: true,
    mfa: true,
    emergencyAccess: false,
  });

  const loadSecurityData = async () => {
    try {
      const statusData = await fetchSecurityStatus();
      setStatus(statusData);
      setToggles({
        autoLogout: statusData.auto_logout_enabled,
        sessionTimeout: statusData.session_timeout_minutes > 0,
        deviceVerification: statusData.device_verification_active,
        mfa: statusData.mfa_enforced,
        emergencyAccess: statusData.emergency_access_mode,
      });

      const auditData = await fetchSecurityAudit();
      setAuditLogs(auditData);
    } catch (err) {
      console.error("Error fetching security data:", err);
    }
  };

  useEffect(() => {
    loadSecurityData();
  }, []);

  const handleToggle = (key) => {
    setToggles((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          🔒 Patient Data Protection & Security
        </h1>
        <p className="text-sm text-surface-muted">
          Active session encryption monitoring, role matrices, and audit logs.
        </p>
      </div>

      {/* Security Status Cards */}
      <SecurityCard status={status} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Permission Matrix */}
        <div className="xl:col-span-2 space-y-6">
          <PermissionMatrix />
          <ComplianceBadges />
        </div>

        {/* Privacy Controls & Log Feed */}
        <div className="space-y-6">
          {/* Privacy Controls Panel */}
          <div className="panel p-5 space-y-4">
            <div>
              <h3 className="label">Privacy & Access Controls</h3>
              <p className="text-xs text-surface-muted mt-1">Configure session policies and credentials controls.</p>
            </div>

            <div className="space-y-3">
              {[
                { key: "autoLogout", label: "Enforce Auto Logout", desc: "Terminates inactive clinician connections." },
                { key: "sessionTimeout", label: "Session Timeout (15m)", desc: "Requires re-auth after interval breach." },
                { key: "deviceVerification", label: "Device Fingerprinting", desc: "Limits intake logging to verified tablets." },
                { key: "mfa", label: "Mandate MFA", desc: "Forces 2-factor verification on shift logins." },
                { key: "emergencyAccess", label: "Emergency Bypass Mode", desc: "Allows temporary access override." },
              ].map((t) => (
                <div key={t.key} className="flex items-center justify-between p-3 bg-accent-wash/20 rounded-xl">
                  <div>
                    <span className="text-xs font-bold text-white block">{t.label}</span>
                    <span className="text-[10px] text-surface-muted leading-tight block mt-0.5">{t.desc}</span>
                  </div>
                  <button
                    onClick={() => handleToggle(t.key)}
                    className={`relative inline-flex h-5.5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      toggles[t.key] ? "bg-accent-blue" : "bg-surface-border"
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4.5 w-4.5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                        toggles[t.key] ? "translate-x-4.5" : "translate-x-0"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Audit Logs */}
          <AuditTimeline logs={auditLogs} />
        </div>
      </div>
    </div>
  );
}
