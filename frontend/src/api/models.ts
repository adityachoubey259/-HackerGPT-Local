import { apiClient } from "./client";
import type {
  ModelTestRequest,
  ModelTestResponse,
  NormalizedModel,
  ProviderHealth
} from "../types/api";

export const modelsApi = {
  providers: (signal?: AbortSignal) =>
    apiClient.get<ProviderHealth[]>("/api/v1/models/providers", { signal }),
  models: (provider?: string, signal?: AbortSignal) => {
    const query = provider ? `?provider=${encodeURIComponent(provider)}` : "";
    return apiClient.get<NormalizedModel[]>(`/api/v1/models${query}`, { signal });
  },
  details: (provider: string, model: string, signal?: AbortSignal) =>
    apiClient.get<NormalizedModel>(
      `/api/v1/models/details?provider=${encodeURIComponent(provider)}&model=${encodeURIComponent(model)}`,
      { signal }
    ),
  test: (request: ModelTestRequest, signal?: AbortSignal) =>
    apiClient.post<ModelTestResponse>("/api/v1/models/test", request, {
      signal,
      timeoutMs: 60000
    })
};
