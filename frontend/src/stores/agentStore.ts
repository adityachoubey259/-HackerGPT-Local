import { create } from "zustand";

import { agentsApi } from "../api/agents";
import { preferencesApi } from "../api/preferences";
import type { AgentDefinition } from "../types/api";

interface AgentStore {
  agents: AgentDefinition[];
  selectedAgentId: string | null;
  loading: boolean;
  loadAgents: () => Promise<void>;
  selectAgent: (agentId: string | null) => void;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  agents: [],
  selectedAgentId: null,
  loading: false,
  loadAgents: async () => {
    set({ loading: true });
    try {
      const agents = await agentsApi.list();
      const preferredAgentId = await loadPreferredAgentId();
      const enabledAgents = agents.filter((agent) => agent.enabled);
      set({
        agents,
        selectedAgentId: resolveSelectedAgentId(
          enabledAgents,
          get().selectedAgentId,
          preferredAgentId
        ),
        loading: false
      });
    } catch {
      set({ agents: [], loading: false });
    }
  },
  selectAgent: (agentId) => set({ selectedAgentId: agentId })
}));

async function loadPreferredAgentId(): Promise<string | null | undefined> {
  try {
    const preferences = await preferencesApi.get();
    return preferences.default_agent;
  } catch {
    return undefined;
  }
}

function resolveSelectedAgentId(
  enabledAgents: AgentDefinition[],
  currentAgentId: string | null,
  preferredAgentId: string | null | undefined
): string | null {
  if (currentAgentId) {
    return currentAgentId;
  }
  if (preferredAgentId === null) {
    return null;
  }
  const requestedAgentId = preferredAgentId ?? "expert";
  const requestedAgent = enabledAgents.find((agent) => agent.id === requestedAgentId);
  if (requestedAgent) {
    return requestedAgent.id;
  }
  const expertAgent = enabledAgents.find((agent) => agent.id === "expert");
  if (expertAgent) {
    return expertAgent.id;
  }
  return enabledAgents.length > 0 ? enabledAgents[0].id : null;
}
