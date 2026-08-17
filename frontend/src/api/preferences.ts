import { apiClient } from "./client";
import type { UserPreferences, UserPreferencesPatch } from "../types/api";

export const preferencesApi = {
  get: (signal?: AbortSignal) => apiClient.get<UserPreferences>("/api/v1/preferences", { signal }),
  patch: (request: UserPreferencesPatch, signal?: AbortSignal) =>
    apiClient.patch<UserPreferences>("/api/v1/preferences", request, { signal })
};
