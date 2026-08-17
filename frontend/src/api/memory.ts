import { apiClient } from "./client";
import type {
  MemoryExportResponse,
  MemoryItem,
  MemoryListResponse,
  MemoryScope,
  MemorySearchResponse,
  MemoryType
} from "../types/api";

export interface MemoryCreateInput {
  memory_type: MemoryType;
  scope: MemoryScope;
  title: string;
  content: string;
  importance: number;
  pinned: boolean;
  enabled: boolean;
  tags: string[];
  conversation_id?: string | null;
  source_message_id?: string | null;
}

export const memoryApi = {
  list(params: { search?: string; memoryType?: string; enabled?: boolean; limit?: number } = {}) {
    const query = new URLSearchParams();
    query.set("limit", String(params.limit ?? 30));
    query.set("offset", "0");
    if (params.search) query.set("search", params.search);
    if (params.memoryType) query.set("memory_type", params.memoryType);
    if (params.enabled !== undefined) query.set("enabled", String(params.enabled));
    return apiClient.get<MemoryListResponse>(`/api/v1/memory?${query.toString()}`);
  },

  create(input: MemoryCreateInput) {
    return apiClient.post<MemoryItem>("/api/v1/memory", input);
  },

  patch(memoryId: string, patch: Partial<MemoryCreateInput>) {
    return apiClient.patch<MemoryItem>(`/api/v1/memory/${memoryId}`, patch);
  },

  delete(memoryId: string) {
    return apiClient.delete<null>(`/api/v1/memory/${memoryId}`);
  },

  search(query: string, limit = 5) {
    return apiClient.post<MemorySearchResponse>("/api/v1/memory/search", {
      query,
      limit
    });
  },

  export() {
    return apiClient.post<MemoryExportResponse>("/api/v1/memory/export", {});
  }
};
