import { createContext, useContext, useState } from "react";

/**
 * SurgeContext — Surge Mode is a CLIENT-SIDE simulation setting, not a
 * backend state. Toggling it here affects the Digital Twin page's
 * arrival-rate multiplier and the Command Center's display banner. It
 * has no effect on the real triage queue or any recommendation — it
 * exists to demonstrate how the system's *display* changes under load,
 * consistent with the platform's principle that surge must never
 * change scoring thresholds, only presentation.
 */
const SurgeContext = createContext(null);

export function SurgeProvider({ children }) {
  const [surge, setSurge] = useState(false);
  return <SurgeContext.Provider value={{ surge, setSurge }}>{children}</SurgeContext.Provider>;
}

export function useSurge() {
  const ctx = useContext(SurgeContext);
  if (!ctx) throw new Error("useSurge must be used within a SurgeProvider");
  return ctx;
}
