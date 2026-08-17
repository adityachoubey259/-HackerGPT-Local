import { ApiClientError, apiClient } from "./client";
import { parseSseStream } from "./sse";
import type { ApiErrorResponse, ChatStreamEvent, ChatStreamRequest } from "../types/api";

export const chatApi = {
  async *stream(
    body: ChatStreamRequest,
    signal: AbortSignal
  ): AsyncGenerator<ChatStreamEvent> {
    const response = await fetch(apiClient.url("/api/v1/chat/stream"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "include",
      signal
    });
    if (!response.ok) {
      throw await normalizeStreamHttpError(response);
    }
    if (!response.body) {
      throw new ApiClientError("Chat stream response had no body.", {
        code: "CHAT_STREAM_EMPTY",
        status: response.status,
        requestId: response.headers.get("X-Request-ID")
      });
    }
    yield* parseSseStream(response.body);
  },

  cancel(generationId: string) {
    return apiClient.post<{ cancelled: boolean }>(
      `/api/v1/chat/generations/${generationId}/cancel`,
      {}
    );
  }
};

async function normalizeStreamHttpError(response: Response): Promise<ApiClientError> {
  const requestId = response.headers.get("X-Request-ID");
  const text = await response.text();
  if (text) {
    try {
      const payload = JSON.parse(text) as unknown;
      if (isApiErrorResponse(payload)) {
        return new ApiClientError(payload.error.message, {
          code: payload.error.code,
          status: response.status,
          requestId: payload.error.request_id || requestId,
          details: payload.error.details
        });
      }
    } catch {
      return new ApiClientError("Chat stream failed with malformed error response.", {
        code: "CHAT_STREAM_MALFORMED_ERROR",
        status: response.status,
        requestId
      });
    }
  }
  return new ApiClientError("Chat stream failed.", {
    code: "CHAT_STREAM_HTTP_ERROR",
    status: response.status,
    requestId
  });
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value) || !isRecord(value.error)) {
    return false;
  }
  return (
    typeof value.error.code === "string" &&
    typeof value.error.message === "string" &&
    typeof value.error.request_id === "string" &&
    isRecord(value.error.details)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}
