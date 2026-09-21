import React, { createContext, useContext, useState } from "react";
import { useDemoStatus } from "../api/useDemoStatus";
import type { DemoStatus } from "../api/client";

interface AgentControlContextType {
  agentsEnabled: boolean;
  setAgentsEnabled: (enabled: boolean) => void;
  toggleAgents: () => void;
  backendReachable: boolean;
  demoStatus: DemoStatus | undefined;
  isLoading: boolean;
  // The real incident_id the Presentation page is following (set when the
  // operator injects a failure); null = fall back to the most recent incident
  // this browser has seen.
  activeIncidentId: string | null;
  setActiveIncidentId: (incidentId: string | null) => void;
}

const AgentControlContext = createContext<AgentControlContextType | undefined>(undefined);

const STORAGE_KEY = "nexus_agents_enabled";

export function AgentControlProvider({ children }: { children: React.ReactNode }) {
  // Default to false as specified in the brief:
  // "Current state should be OFF because the backend is probably offline."
  const [agentsEnabled, setAgentsEnabledState] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored !== null ? JSON.parse(stored) : false;
    } catch {
      return false;
    }
  });

  const [activeIncidentId, setActiveIncidentId] = useState<string | null>(null);
  const demoStatusQuery = useDemoStatus();
  const backendReachable = Boolean(demoStatusQuery.isSuccess && demoStatusQuery.data);

  const setAgentsEnabled = (enabled: boolean) => {
    setAgentsEnabledState(enabled);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(enabled));
    } catch {
      // ignore storage error
    }
  };

  const toggleAgents = () => {
    setAgentsEnabled(!agentsEnabled);
  };

  return (
    <AgentControlContext.Provider
      value={{
        agentsEnabled,
        setAgentsEnabled,
        toggleAgents,
        backendReachable,
        demoStatus: demoStatusQuery.data,
        isLoading: demoStatusQuery.isLoading,
        activeIncidentId,
        setActiveIncidentId,
      }}
    >
      {children}
    </AgentControlContext.Provider>
  );
}

export function useAgentControl() {
  const context = useContext(AgentControlContext);
  if (!context) {
    throw new Error("useAgentControl must be used within an AgentControlProvider");
  }
  return context;
}
