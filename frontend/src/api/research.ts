import { apiClient } from "./client";
import type {
  ResearchHistoryResponse,
  ResearchRunResponse,
  ResearchStatus
} from "../types/api";

export const researchApi = {
  status: () => apiClient.get<ResearchStatus>("/api/v1/research/status"),
  history: () => apiClient.get<ResearchHistoryResponse>("/api/v1/research/history"),
  run: (body: { query: string; max_results?: number; official_only?: boolean }) =>
    apiClient.post<ResearchRunResponse>("/api/v1/research/run", body, { timeoutMs: 20000 })
};
