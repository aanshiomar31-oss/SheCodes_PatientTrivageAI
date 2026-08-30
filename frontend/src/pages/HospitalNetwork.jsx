import { useState } from "react";
import HospitalSelector from "../components/HospitalSelector.jsx";
import CapacityCard from "../components/CapacityCard.jsx";
import SpecialtyToggle from "../components/SpecialtyToggle.jsx";
import NetworkMap from "../components/NetworkMap.jsx";
import DeploymentMode from "../components/DeploymentMode.jsx";
import PriorityBadge from "../components/PriorityBadge.jsx";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { motion } from "framer-motion";

// Mock patient mixes for each hospital and department
const MOCK_PATIENT_LISTS = {
  rural: {
    general: [
      { stay_id: 101, patient_id: "ED0101", priority: "P3", chief_complaint: "Abdominal discomfort, low-grade fever", age: 34, waited_minutes: 42, resprate: 18, o2sat: 97 },
      { stay_id: 102, patient_id: "ED0102", priority: "P4", chief_complaint: "Ankle sprain after slip and fall", age: 22, waited_minutes: 58, resprate: 14, o2sat: 99 },
      { stay_id: 103, patient_id: "ED0103", priority: "P2", chief_complaint: "Severe dyspnea, COPD flare-up", age: 68, waited_minutes: 10, resprate: 24, o2sat: 92 },
    ],
    peds: [
      { stay_id: 104, patient_id: "ED0104", priority: "P3", chief_complaint: "Pediatric earache, crying, vomiting", age: 3, waited_minutes: 15, resprate: 22, o2sat: 98 },
    ],
    trauma: [
      { stay_id: 105, patient_id: "ED0105", priority: "P3", chief_complaint: "Deep laceration to finger from kitchen knife", age: 41, waited_minutes: 25, resprate: 16, o2sat: 99 },
    ],
    cardiology: [
      { stay_id: 106, patient_id: "ED0106", priority: "P1", chief_complaint: "Chest pressure, history of CABG", age: 60, waited_minutes: 2, resprate: 20, o2sat: 95 },
    ],
    stroke: [
      { stay_id: 107, patient_id: "ED0107", priority: "P2", chief_complaint: "Sudden slurred speech, resolved", age: 79, waited_minutes: 12, resprate: 16, o2sat: 98 },
    ],
  },
  district: {
    general: [
      { stay_id: 201, patient_id: "ED0201", priority: "P2", chief_complaint: "Chest pain with mild diaphoresis", age: 54, waited_minutes: 12, resprate: 20, o2sat: 96 },
      { stay_id: 202, patient_id: "ED0202", priority: "P3", chief_complaint: "Dehydration, diabetic ketoacidosis risk", age: 29, waited_minutes: 24, resprate: 18, o2sat: 98 },
      { stay_id: 203, patient_id: "ED0203", priority: "P4", chief_complaint: "Simple wrist deformity post fall", age: 15, waited_minutes: 48, resprate: 14, o2sat: 99 },
      { stay_id: 204, patient_id: "ED0204", priority: "P1", chief_complaint: "Anaphylaxis to peanut, respiratory distress", age: 9, waited_minutes: 1, resprate: 28, o2sat: 89 },
    ],
    peds: [
      { stay_id: 205, patient_id: "ED0205", priority: "P3", chief_complaint: "Pediatric high fever (103F), croupy cough", age: 2, waited_minutes: 10, resprate: 30, o2sat: 96 },
    ],
    trauma: [
      { stay_id: 206, patient_id: "ED0206", priority: "P2", chief_complaint: "Multiple fractures, stable vital signs", age: 33, waited_minutes: 18, resprate: 18, o2sat: 98 },
    ],
    cardiology: [
      { stay_id: 207, patient_id: "ED0207", priority: "P1", chief_complaint: "Substernal crushing pain, diaphoresis", age: 62, waited_minutes: 2, resprate: 22, o2sat: 94 },
    ],
    stroke: [
      { stay_id: 208, patient_id: "ED0208", priority: "P1", chief_complaint: "FAST-positive: sudden left-sided weakness", age: 74, waited_minutes: 3, resprate: 16, o2sat: 97 },
    ],
  },
  urban: {
    general: [
      { stay_id: 301, patient_id: "ED0301", priority: "P1", chief_complaint: "Cardiac arrest, active CPR in transit", age: 67, waited_minutes: 0, resprate: 0, o2sat: 0 },
      { stay_id: 302, patient_id: "ED0302", priority: "P1", chief_complaint: "Gunshot wound to abdomen, hypotensive", age: 24, waited_minutes: 1, resprate: 24, o2sat: 91 },
      { stay_id: 303, patient_id: "ED0303", priority: "P2", chief_complaint: "Head trauma, LOC, confusion", age: 39, waited_minutes: 8, resprate: 18, o2sat: 96 },
      { stay_id: 304, patient_id: "ED0304", priority: "P3", chief_complaint: "Possible hip fracture, severe pain", age: 83, waited_minutes: 22, resprate: 20, o2sat: 97 },
      { stay_id: 305, patient_id: "ED0305", priority: "P4", chief_complaint: "Minor burn to forearm from boiling water", age: 45, waited_minutes: 65, resprate: 16, o2sat: 99 },
    ],
    peds: [
      { stay_id: 306, patient_id: "ED0306", priority: "P1", chief_complaint: "Neonate fever (38.5C) under 28 days", age: 0.05, waited_minutes: 2, resprate: 45, o2sat: 95 },
      { stay_id: 307, patient_id: "ED0307", priority: "P3", chief_complaint: "Pediatric asthma, mild wheeze", age: 7, waited_minutes: 14, resprate: 24, o2sat: 97 },
    ],
    trauma: [
      { stay_id: 308, patient_id: "ED0308", priority: "P1", chief_complaint: "Level 1 trauma: multi-system crush injury", age: 28, waited_minutes: 2, resprate: 26, o2sat: 92 },
      { stay_id: 309, patient_id: "ED0309", priority: "P2", chief_complaint: "Open tibia fracture, severe deformity", age: 31, waited_minutes: 11, resprate: 20, o2sat: 98 },
    ],
    cardiology: [
      { stay_id: 310, patient_id: "ED0310", priority: "P1", chief_complaint: "STEMI activation, substernal crushing pain", age: 59, waited_minutes: 3, resprate: 22, o2sat: 93 },
      { stay_id: 311, patient_id: "ED0311", priority: "P2", chief_complaint: "New-onset atrial fibrillation with RVR", age: 71, waited_minutes: 12, resprate: 18, o2sat: 97 },
    ],
    stroke: [
      { stay_id: 312, patient_id: "ED0312", priority: "P1", chief_complaint: "Acute stroke symptoms within 2-hour window", age: 80, waited_minutes: 4, resprate: 16, o2sat: 98 },
    ],
  },
};

export default function HospitalNetwork() {
  const [activeHospital, setActiveHospital] = useState("district");
  const [activeSpecialty, setActiveSpecialty] = useState("general");

  const patients = MOCK_PATIENT_LISTS[activeHospital][activeSpecialty] || [];

  // Generate Recharts priority mix dynamically
  const chartColors = { P1: "#f87171", P2: "#fb923c", P3: "#facc15", P4: "#4ade80", P5: "#60a5fa" };
  const priorityDistribution = ["P1", "P2", "P3", "P4", "P5"].map((p) => ({
    priority: p,
    count: patients.filter((pt) => pt.priority === p).length,
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          🏥 Regional Hospital Network Coordination
        </h1>
        <p className="text-sm text-surface-muted">
          Inspect federated queues, referral loads, and load-balance patients dynamically.
        </p>
      </div>

      {/* Hospital Node Switcher */}
      <HospitalSelector selectedId={activeHospital} onSelect={setActiveHospital} />

      {/* Active Capacity Metrics Card */}
      <CapacityCard hospitalId={activeHospital} />

      {/* Specialty Filter Toggle */}
      <SpecialtyToggle selectedId={activeSpecialty} onSelect={setActiveSpecialty} />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Dynamic Queue Preview List */}
        <div className="xl:col-span-2 panel p-5 space-y-4">
          <div className="flex justify-between items-center border-b border-surface-border pb-3">
            <div>
              <h3 className="label">Federated Queue Preview</h3>
              <p className="text-xs text-surface-muted mt-1">Live patients matching selected specialty department.</p>
            </div>
            <span className="text-[10px] text-surface-muted font-bold uppercase">
              Count: {patients.length} Stays
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-surface-border text-surface-muted">
                  <th className="py-2.5 font-bold uppercase">Stay ID</th>
                  <th className="py-2.5 font-bold uppercase">Priority</th>
                  <th className="py-2.5 font-bold uppercase">Chief Complaint</th>
                  <th className="py-2.5 font-bold uppercase">Age</th>
                  <th className="py-2.5 font-bold uppercase text-right">Wait Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border text-white">
                {patients.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-surface-muted">
                      No patients in this department mix currently.
                    </td>
                  </tr>
                ) : (
                  patients.map((pt) => (
                    <tr key={pt.stay_id} className="hover:bg-accent-wash/20">
                      <td className="py-3 font-semibold">#{pt.stay_id}</td>
                      <td className="py-3">
                        <PriorityBadge priority={pt.priority} compact />
                      </td>
                      <td className="py-3 text-surface-muted">{pt.chief_complaint}</td>
                      <td className="py-3">{Math.round(pt.age)}</td>
                      <td className="py-3 text-right text-accent-mint font-semibold">{pt.waited_minutes}m</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Priority Mix Chart */}
        <div className="panel p-5 flex flex-col justify-between">
          <div>
            <h3 className="label">Department Acuity Distribution</h3>
            <p className="text-xs text-surface-muted mt-1">Ratio of patient acuity mix in this ward.</p>
          </div>
          
          <div className="h-44 mt-4">
            {patients.length === 0 ? (
              <p className="text-xs text-surface-muted text-center py-12">No mix data available.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={priorityDistribution} margin={{ left: -25, right: 10, top: 10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2C4E3D" vertical={false} />
                  <XAxis dataKey="priority" stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 10 }} />
                  <YAxis allowDecimals={false} stroke="#8CA397" tick={{ fill: "#8CA397", fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: "#1F3A2D", border: "1px solid #2C4E3D", borderRadius: 12, color: "#fff" }} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {priorityDistribution.map((d) => (
                      <Cell key={d.priority} fill={chartColors[d.priority] || "#60a5fa"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="border-t border-surface-border pt-3 mt-4 text-[10px] text-surface-muted text-center leading-relaxed">
            *Acuity mix updates instantly when switching hospitals or specialty departments.
          </div>
        </div>
      </div>

      {/* SVG Network Map and Deployment Topologies */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <NetworkMap activeHospitalId={activeHospital} />
        <DeploymentMode />
      </div>
    </div>
  );
}

// Subcomponent: Cell helper for Recharts Bar Chart
function Cell({ fill, ...props }) {
  return <rect fill={fill} {...props} />;
}
