import type { ApiErrorResponse } from "../types/api";

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export class ApiClientError extends Error {
  readonly code: string;
  readonly status: number | null;
  readonly requestId: string | null;
  readonly details: Record<string, unknown>;

  constructor(
    message: string,
    options: {
      code: string;
      status: number | null;
      requestId?: string | null;
      details?: Record<string, unknown>;
    }
  ) {
    super(message);
    this.name = "ApiClientError";
    this.code = options.code;
    this.status = options.status;
    this.requestId = options.requestId ?? null;
    this.details = options.details ?? {};
  }
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly defaultTimeoutMs: number;

  constructor(baseUrl: string = import.meta.env.VITE_HACKERGPT_API_BASE_URL ?? "http://127.0.0.1:8000") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.defaultTimeoutMs = 8000;
  }

  async get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { method: "GET" }, options);
  }

  async post<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(
      path,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      },
      options
    );
  }

  async patch<T>(path: string, body: unknown, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(
      path,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      },
      options
    );
  }

  async delete<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, { method: "DELETE" }, options);
  }

  url(path: string): string {
    return `${this.baseUrl}${path}`;
  }

  private async request<T>(
    path: string,
    init: RequestInit,
    options: RequestOptions
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = window.setTimeout(
      () => controller.abort(),
      options.timeoutMs ?? this.defaultTimeoutMs
    );
    if (options.signal) {
      options.signal.addEventListener("abort", () => controller.abort(), { once: true });
    }
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        credentials: "include",
        signal: controller.signal
      });
      const requestId = response.headers.get("X-Request-ID");
      const payload = await parseJson(response);
      if (!response.ok) {
        throw normalizeHttpError(response.status, requestId, payload);
      }
      return payload as T;
    } catch (error) {
      if (error instanceof ApiClientError) {
        throw error;
      }
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ApiClientError("Request timed out or was aborted.", {
          code: "REQUEST_TIMEOUT",
          status: null
        });
      }
      throw new ApiClientError("Backend is offline or unreachable.", {
        code: "BACKEND_OFFLINE",
        status: null
      });
    } finally {
      window.clearTimeout(timeout);
    }
  }
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new ApiClientError("Backend returned malformed JSON.", {
      code: "MALFORMED_RESPONSE",
      status: response.status,
      requestId: response.headers.get("X-Request-ID")
    });
  }
}

function normalizeHttpError(
  status: number,
  requestId: string | null,
  payload: unknown
): ApiClientError {
  if (isApiErrorResponse(payload)) {
    return new ApiClientError(payload.error.message, {
      code: payload.error.code,
      status,
      requestId: payload.error.request_id || requestId,
      details: payload.error.details
    });
  }
  return new ApiClientError("Backend returned an error.", {
    code: "HTTP_ERROR",
    status,
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

export const apiClient = new ApiClient();
