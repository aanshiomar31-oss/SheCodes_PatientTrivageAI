import { useState } from "react";
import { motion } from "framer-motion";

const MATRIX_DATA = [
  { permission: "View Queue", nurse: true, doctor: true, admin: true },
  { permission: "Intake Triage", nurse: true, doctor: true, admin: true },
  { permission: "Record Override", nurse: true, doctor: true, admin: true },
  { permission: "Audit Log Inspection", nurse: false, doctor: true, admin: true },
  { permission: "Deregister Patient Stays", nurse: false, doctor: false, admin: true },
  { permission: "Retrain Acuity Models", nurse: false, doctor: false, admin: true },
  { permission: "Modify Compliance Settings", nurse: false, doctor: false, admin: true },
];

export default function PermissionMatrix() {
  const [selectedRole, setSelectedRole] = useState(null);

  return (
    <div className="panel p-5 space-y-4">
      <div>
        <h3 className="label">Role-Based Access Control (RBAC) Matrix</h3>
        <p className="text-xs text-surface-muted mt-1">Authorized actions mapped by clinical personnel role.</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-surface-border">
              <th className="py-3 text-surface-muted uppercase font-bold">Clinical Action</th>
              <th className={`py-3 text-center cursor-pointer transition uppercase font-bold ${selectedRole === "nurse" ? "text-accent-mint" : "text-surface-muted"}`} onClick={() => setSelectedRole("nurse")}>Nurse</th>
              <th className={`py-3 text-center cursor-pointer transition uppercase font-bold ${selectedRole === "doctor" ? "text-accent-mint" : "text-surface-muted"}`} onClick={() => setSelectedRole("doctor")}>Doctor</th>
              <th className={`py-3 text-center cursor-pointer transition uppercase font-bold ${selectedRole === "admin" ? "text-accent-mint" : "text-surface-muted"}`} onClick={() => setSelectedRole("admin")}>Admin</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {MATRIX_DATA.map((row) => (
              <tr key={row.permission} className="hover:bg-accent-wash/20">
                <td className="py-3.5 text-white font-medium">{row.permission}</td>
                <td className="py-3.5 text-center">
                  <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${row.nurse ? "bg-accent-wash text-accent-mint" : "bg-red-500/10 text-red-400"}`}>
                    {row.nurse ? "✓ Allowed" : "✗ Denied"}
                  </span>
                </td>
                <td className="py-3.5 text-center">
                  <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${row.doctor ? "bg-accent-wash text-accent-mint" : "bg-red-500/10 text-red-400"}`}>
                    {row.doctor ? "✓ Allowed" : "✗ Denied"}
                  </span>
                </td>
                <td className="py-3.5 text-center">
                  <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${row.admin ? "bg-accent-wash text-accent-mint" : "bg-red-500/10 text-red-400"}`}>
                    {row.admin ? "✓ Allowed" : "✗ Denied"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedRole && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-accent-wash border border-accent-mint/30 rounded-xl p-4 text-xs space-y-2 mt-4"
        >
          <div className="flex justify-between items-center">
            <h4 className="font-bold text-white capitalize">{selectedRole} Privileges Overview</h4>
            <button onClick={() => setSelectedRole(null)} className="text-[10px] text-surface-muted hover:text-white">Clear ×</button>
          </div>
          <p className="text-surface-muted leading-relaxed">
            {selectedRole === "nurse" && "Nurses have full triage, override, and queue review rights, ensuring continuous patient care workflows. Advanced system and model options are restricted."}
            {selectedRole === "doctor" && "Doctors possess full operational access including queue triage and overrides, with addition of clinical log inspection permissions for audit purposes."}
            {selectedRole === "admin" && "Administrators have comprehensive root privileges, including database migrations, ML model retraining pipelines, and compliance verification overrides."}
          </p>
        </motion.div>
      )}
    </div>
  );
}
