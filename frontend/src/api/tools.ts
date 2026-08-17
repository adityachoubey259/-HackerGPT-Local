import { apiClient } from "./client";
import type {
  ToolConfirmation,
  ToolDefinition,
  ToolExecuteResponse,
  ToolExecution,
  ToolExecutionListResponse
} from "../types/api";

export const toolsApi = {
  async list(signal?: AbortSignal) {
    const response = await apiClient.get<{ items: ToolDefinition[] }>("/api/v1/tools", {
      signal
    });
    return response.items;
  },

  execute(body: {
    tool_name: string;
    arguments: Record<string, unknown>;
    conversation_id?: string | null;
    agent_id?: string | null;
  }) {
    return apiClient.post<ToolExecuteResponse>("/api/v1/tools/execute", body, {
      timeoutMs: 30000
    });
  },

  history(signal?: AbortSignal) {
    return apiClient.get<ToolExecutionListResponse>("/api/v1/tools/executions", { signal });
  },

  confirmations(signal?: AbortSignal) {
    return apiClient.get<ToolConfirmation[]>("/api/v1/tools/confirmations", { signal });
  },

  approve(confirmationId: string) {
    return apiClient.post<{ execution: ToolExecution; confirmation: ToolConfirmation }>(
      `/api/v1/tools/confirmations/${confirmationId}/approve`,
      {},
      { timeoutMs: 30000 }
    );
  },

  deny(confirmationId: string) {
    return apiClient.post<{ execution: ToolExecution; confirmation: ToolConfirmation }>(
      `/api/v1/tools/confirmations/${confirmationId}/deny`,
      {}
    );
  }
};
