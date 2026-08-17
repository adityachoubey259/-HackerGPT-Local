import { apiClient } from "./client";
import type {
  HardwareReport,
  HealthResponse,
  KnowledgeMemoryStatus,
  PublicConfig,
  SystemInfo
} from "../types/api";

export const systemApi = {
  health: (signal?: AbortSignal) => apiClient.get<HealthResponse>("/api/v1/health", { signal }),
  info: (signal?: AbortSignal) => apiClient.get<SystemInfo>("/api/v1/system/info", { signal }),
  hardware: (signal?: AbortSignal) =>
    apiClient.get<HardwareReport>("/api/v1/system/hardware", { signal }),
  knowledgeMemory: (signal?: AbortSignal) =>
    apiClient.get<KnowledgeMemoryStatus>("/api/v1/system/knowledge-memory", { signal }),
  publicConfig: (signal?: AbortSignal) =>
    apiClient.get<PublicConfig>("/api/v1/config/public", { signal })
};
