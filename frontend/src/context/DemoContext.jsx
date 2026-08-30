import { createContext, useContext, useState, useEffect } from "react";
import { submitTriage, fetchQueue, submitOverride, updateVitals } from "../services/api.js";

const DemoContext = createContext(null);

const MOCK_COMPLAINTS = [
  { chief_complaint: "Substernal chest pressure radiating to left arm", chest_pain: true, diaphoresis: true, age: 58, gender: "M", heartrate: 98, sbp: 142, dbp: 88, resprate: 20, o2sat: 96, temperature: 98.6, pain: 8 },
  { chief_complaint: "Sudden onset right-sided weakness and facial droop", fast_positive: true, age: 72, gender: "F", heartrate: 84, sbp: 165, dbp: 95, resprate: 16, o2sat: 98, temperature: 97.9, pain: 0 },
  { chief_complaint: "Severe respiratory distress, wheezing, using accessory muscles", resprate: 32, o2sat: 88, age: 45, gender: "F", heartrate: 115, sbp: 130, dbp: 80, temperature: 99.1, pain: 4 },
  { chief_complaint: "Found unresponsive at home by family, shallow breathing", unresponsive: true, age: 81, gender: "M", heartrate: 55, sbp: 90, dbp: 50, resprate: 10, o2sat: 91, temperature: 96.2, pain: 0 },
  { chief_complaint: "Active generalized tonic-clonic seizure starting 10m ago", seizing: true, age: 29, gender: "M", heartrate: 135, sbp: 150, dbp: 90, resprate: 24, o2sat: 94, temperature: 100.2, pain: 0 },
  { chief_complaint: "High fever, lethargy, poor feeding in 3-week-old infant", age: 0.08, gender: "F", heartrate: 165, sbp: 75, dbp: 45, resprate: 52, o2sat: 97, temperature: 101.3, pain: 2 },
  { chief_complaint: "Deep laceration to right forearm with active arterial bleeding", pain: 9, age: 34, gender: "M", heartrate: 108, sbp: 110, dbp: 70, resprate: 18, o2sat: 99, temperature: 98.4 },
  { chief_complaint: "Generalized abdominal pain, nausea, and vomiting for 2 days", pain: 7, age: 24, gender: "F", heartrate: 88, sbp: 118, dbp: 76, resprate: 16, o2sat: 99, temperature: 100.8 }
];

const OVERRIDE_REASONS = [
  "Clinical presentation and visual assessment show higher distress than vitals suggest",
  "Patient has significant comorbidities (brittle diabetes, stage IV CKD)",
  "Resource utilization requirements suggest fast-track to minor care",
  "Abnormal vitals resolved upon repeating measurement, patient stable",
  "Social/placement issues requiring direct physician consult"
];

export function DemoProvider({ children }) {
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    if (!demo) return;

    // Simulation loops:
    // 1. Create a new patient intake every 25 seconds
    const intakeInterval = setInterval(async () => {
      try {
        const mock = MOCK_COMPLAINTS[Math.floor(Math.random() * MOCK_COMPLAINTS.length)];
        const suffix = Math.floor(1000 + Math.random() * 9000);
        const payload = {
          ...mock,
          arrival_transport: Math.random() > 0.4 ? "WALK IN" : "AMBULANCE",
          arrival_hour: new Date().getHours(),
          night_shift_flag: new Date().getHours() < 7 || new Date().getHours() > 19,
          weekend_flag: [0, 6].includes(new Date().getDay()),
          medications: Math.random() > 0.5 ? ["Aspirin", "Metoprolol"] : [],
          zero_history: Math.random() > 0.7
        };
        await submitTriage(payload);
        console.log("Demo Mode: Automated intake submitted for new mock patient");
      } catch (err) {
        console.error("Demo Mode intake error:", err);
      }
    }, 25000);

    // 2. Perform a priority override on a patient in the queue every 40 seconds
    const overrideInterval = setInterval(async () => {
      try {
        const queueData = await fetchQueue("priority");
        const entries = queueData?.entries ?? [];
        // Filter patients that are not already overridden and aren't P1
        const candidates = entries.filter(e => !e.overridden && e.priority !== "P1");
        if (candidates.length > 0) {
          const target = candidates[Math.floor(Math.random() * candidates.length)];
          const priorities = ["P1", "P2", "P3", "P4", "P5"];
          let newP = target.priority;
          while (newP === target.priority) {
            newP = priorities[Math.floor(Math.random() * priorities.length)];
          }
          await submitOverride({
            stayId: target.stay_id,
            originalPriority: target.priority,
            newPriority: newP,
            reason: OVERRIDE_REASONS[Math.floor(Math.random() * OVERRIDE_REASONS.length)],
            actor: "nurse"
          });
          console.log(`Demo Mode: Automated override submitted for Stay #${target.stay_id}`);
        }
      } catch (err) {
        console.error("Demo Mode override error:", err);
      }
    }, 40000);

    // 3. Re-assess patient vitals every 30 seconds (simulating patient evolution)
    const reassessInterval = setInterval(async () => {
      try {
        const queueData = await fetchQueue("priority");
        const entries = queueData?.entries ?? [];
        if (entries.length > 0) {
          const target = entries[Math.floor(Math.random() * entries.length)];
          // Slightly fluctuate vitals
          const hrDelta = Math.floor(Math.random() * 15) - 7;
          const sbpDelta = Math.floor(Math.random() * 20) - 10;
          const o2satDelta = Math.floor(Math.random() * 5) - 3;

          const updatedVitals = {
            heart_rate: Math.max(50, Math.min(180, (target.heartrate || 80) + hrDelta)),
            sbp: Math.max(80, Math.min(200, (target.sbp || 120) + sbpDelta)),
            o2_sat: Math.max(80, Math.min(100, (target.o2sat || 98) + o2satDelta))
          };

          await updateVitals(target.stay_id, updatedVitals);
          console.log(`Demo Mode: Automated vitals reassessment submitted for Stay #${target.stay_id}`);
        }
      } catch (err) {
        console.error("Demo Mode reassessment error:", err);
      }
    }, 30000);

    return () => {
      clearInterval(intakeInterval);
      clearInterval(overrideInterval);
      clearInterval(reassessInterval);
    };
  }, [demo]);

  return (
    <DemoContext.Provider value={{ demo, setDemo }}>
      {children}
    </DemoContext.Provider>
  );
}

export function useDemo() {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error("useDemo must be used within a DemoProvider");
  return ctx;
}
