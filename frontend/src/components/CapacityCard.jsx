import { motion } from "framer-motion";

export default function CapacityCard({ hospitalId }) {
  // Dynamically resolve metrics based on the active hospital node
  const getMetrics = () => {
    switch (hospitalId) {
      case "rural":
        return [
          { label: "Bed Occupancy", value: "8 / 12", sub: "66.7% capacity", color: "text-white" },
          { label: "Waiting Patients", value: "14", sub: "Awaiting triage/bed assignment", color: "text-accent-mint" },
          { label: "Critical Patients (P1)", value: "1", sub: "1 active intervention", color: "text-red-400" },
          { label: "Average Wait Time", value: "42 min", sub: "Safest wait targets: 60m", color: "text-white" },
          { label: "Nurse Workload", value: "3.5", sub: "Patients per active nurse", color: "text-white" },
        ];
      case "district":
        return [
          { label: "Bed Occupancy", value: "34 / 40", sub: "85.0% capacity", color: "text-white" },
          { label: "Waiting Patients", value: "28", sub: "Awaiting triage/bed assignment", color: "text-accent-mint" },
          { label: "Critical Patients (P1)", value: "3", sub: "2 active interventions", color: "text-red-400" },
          { label: "Average Wait Time", value: "28 min", sub: "Safest wait targets: 30m", color: "text-white" },
          { label: "Nurse Workload", value: "1.9", sub: "Patients per active nurse", color: "text-white" },
        ];
      case "urban":
      default:
        return [
          { label: "Bed Occupancy", value: "104 / 120", sub: "86.7% capacity", color: "text-white" },
          { label: "Waiting Patients", value: "84", sub: "Awaiting triage/bed assignment", color: "text-accent-mint" },
          { label: "Critical Patients (P1)", value: "12", sub: "8 active interventions", color: "text-red-400" },
          { label: "Average Wait Time", value: "15 min", sub: "Safest wait targets: 15m", color: "text-white" },
          { label: "Nurse Workload", value: "1.8", sub: "Patients per active nurse", color: "text-white" },
        ];
    }
  };

  const metrics = getMetrics();

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
      {metrics.map((m, idx) => (
        <motion.div
          key={m.label + hospitalId}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2, delay: idx * 0.05 }}
          className="panel p-5 flex flex-col justify-between"
        >
          <div>
            <span className="label block">{m.label}</span>
            <span className={`mt-3 block text-3xl font-extrabold tracking-tight ${m.color}`}>
              {m.value}
            </span>
          </div>
          <span className="mt-2 block text-[10px] text-surface-muted leading-tight">
            {m.sub}
          </span>
        </motion.div>
      ))}
    </div>
  );
}
