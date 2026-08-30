import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { SurgeProvider } from "./context/SurgeContext.jsx";
import { DemoProvider } from "./context/DemoContext.jsx";
import CommandCenter from "./pages/CommandCenter.jsx";
import PatientIntake from "./pages/PatientIntake.jsx";
import LiveQueue from "./pages/LiveQueue.jsx";
import PatientComparison from "./pages/PatientComparison.jsx";
import Explainability from "./pages/Explainability.jsx";
import AuditLogs from "./pages/AuditLogs.jsx";
import DigitalTwin from "./pages/DigitalTwin.jsx";
import TrustCenter from "./pages/TrustCenter.jsx";
import Security from "./pages/Security.jsx";
import HospitalNetwork from "./pages/HospitalNetwork.jsx";

/**
 * App — top-level route table for the Emergency Department Command Center.
 *
 * Wrapped in SurgeProvider and DemoProvider to manage global simulation and surge states.
 */
export default function App() {
  return (
    <DemoProvider>
      <SurgeProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/intake" element={<PatientIntake />} />
            <Route path="/queue" element={<LiveQueue />} />
            <Route path="/comparison" element={<PatientComparison />} />
            <Route path="/explainability" element={<Explainability />} />
            <Route path="/trust-center" element={<TrustCenter />} />
            <Route path="/security" element={<Security />} />
            <Route path="/hospital-network" element={<HospitalNetwork />} />
            <Route path="/audit" element={<AuditLogs />} />
            <Route path="/digital-twin" element={<DigitalTwin />} />
          </Routes>
        </Layout>
      </SurgeProvider>
    </DemoProvider>
  );
}
