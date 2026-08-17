import { ApiClientError, apiClient } from "./client";
import type {
  IngestionJob,
  KnowledgeDetailResponse,
  KnowledgeListResponse,
  KnowledgeSearchResponse,
  KnowledgeStats
} from "../types/api";

export const knowledgeApi = {
  list(params: { search?: string; status?: string; limit?: number; offset?: number } = {}) {
    const query = new URLSearchParams();
    query.set("limit", String(params.limit ?? 30));
    query.set("offset", String(params.offset ?? 0));
    if (params.search) query.set("search", params.search);
    if (params.status) query.set("status", params.status);
    return apiClient.get<KnowledgeListResponse>(`/api/v1/knowledge?${query.toString()}`);
  },

  stats(signal?: AbortSignal) {
    return apiClient.get<KnowledgeStats>("/api/v1/knowledge/stats", { signal });
  },

  detail(documentId: string) {
    return apiClient.get<KnowledgeDetailResponse>(`/api/v1/knowledge/${documentId}`);
  },

  ingestPath(path: string, tags: string[] = []) {
    return apiClient.post<IngestionJob[]>("/api/v1/knowledge/ingest-path", { path, tags });
  },

  reindex(documentId: string) {
    return apiClient.post<IngestionJob>(`/api/v1/knowledge/${documentId}/reindex`, {});
  },

  delete(documentId: string) {
    return apiClient.delete<null>(`/api/v1/knowledge/${documentId}`);
  },

  search(query: string, limit = 5) {
    return apiClient.post<KnowledgeSearchResponse>("/api/v1/knowledge/search", {
      query,
      limit,
      document_ids: [],
      tags: []
    });
  },

  async upload(file: File, tags: string[] = []): Promise<IngestionJob> {
    const form = new FormData();
    form.append("file", file);
    form.append("tags", tags.join(","));
    const response = await fetch(apiClient.url("/api/v1/knowledge/upload"), {
      method: "POST",
      body: form
    });
    if (!response.ok) {
      throw new ApiClientError("Upload failed.", {
        code: "UPLOAD_FAILED",
        status: response.status,
        requestId: response.headers.get("X-Request-ID")
      });
    }
    return (await response.json()) as IngestionJob;
  }
};
