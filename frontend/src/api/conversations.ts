import { apiClient } from "./client";
import type {
  Conversation,
  ConversationListResponse,
  MessageListResponse
} from "../types/api";

export const conversationsApi = {
  list(params: { limit?: number; offset?: number; archived?: boolean | null; search?: string } = {}) {
    const searchParams = new URLSearchParams();
    searchParams.set("limit", String(params.limit ?? 30));
    searchParams.set("offset", String(params.offset ?? 0));
    if (params.archived !== null) {
      searchParams.set("archived", String(params.archived ?? false));
    }
    if (params.search?.trim()) {
      searchParams.set("search", params.search.trim());
    }
    return apiClient.get<ConversationListResponse>(`/api/v1/conversations?${searchParams}`);
  },
  create(title?: string | null) {
    return apiClient.post<Conversation>("/api/v1/conversations", { title: title ?? null });
  },
  patch(id: string, body: { title?: string; archived?: boolean }) {
    return apiClient.patch<Conversation>(`/api/v1/conversations/${id}`, body);
  },
  delete(id: string) {
    return apiClient.delete<null>(`/api/v1/conversations/${id}`);
  },
  messages(id: string, params: { limit?: number; offset?: number } = {}) {
    const searchParams = new URLSearchParams();
    searchParams.set("limit", String(params.limit ?? 100));
    searchParams.set("offset", String(params.offset ?? 0));
    return apiClient.get<MessageListResponse>(
      `/api/v1/conversations/${id}/messages?${searchParams}`
    );
  }
};
