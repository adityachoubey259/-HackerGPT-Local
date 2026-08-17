import { apiClient } from "./client";
import type { AgentDefinition } from "../types/api";

export const agentsApi = {
  list(signal?: AbortSignal) {
    return apiClient.get<AgentDefinition[]>("/api/v1/agents", { signal });
  },

  get(agentId: string, signal?: AbortSignal) {
    return apiClient.get<AgentDefinition>(`/api/v1/agents/${agentId}`, { signal });
  },

  create(body: {
    id?: string;
    name: string;
    description: string;
    system_prompt: string;
    configuration: Record<string, unknown>;
    enabled: boolean;
  }) {
    return apiClient.post<AgentDefinition>("/api/v1/agents", body);
  },

  duplicate(agentId: string) {
    return apiClient.post<AgentDefinition>(`/api/v1/agents/${agentId}/duplicate`, {});
  },

  patch(
    agentId: string,
    body: Partial<{
      name: string;
      description: string;
      system_prompt: string;
      configuration: Record<string, unknown>;
      enabled: boolean;
    }>
  ) {
    return apiClient.patch<AgentDefinition>(`/api/v1/agents/${agentId}`, body);
  },

  delete(agentId: string) {
    return apiClient.delete<null>(`/api/v1/agents/${agentId}`);
  }
};
