import { apiClient } from "./client";
import type { AuthSession, ChangePasswordRequest, LoginRequest } from "../types/api";

export const authApi = {
  login: (request: LoginRequest, signal?: AbortSignal) =>
    apiClient.post<AuthSession>("/api/v1/auth/login", request, { signal }),
  logout: (signal?: AbortSignal) => apiClient.post<AuthSession>("/api/v1/auth/logout", {}, { signal }),
  me: (signal?: AbortSignal) => apiClient.get<AuthSession>("/api/v1/auth/me", { signal }),
  changePassword: (request: ChangePasswordRequest, signal?: AbortSignal) =>
    apiClient.post<AuthSession>("/api/v1/auth/change-password", request, { signal })
};
