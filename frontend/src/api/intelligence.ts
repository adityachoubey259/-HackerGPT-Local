import { apiClient } from "./client";
import type { ModelCapabilityProfile, RoutingDecision } from "../types/api";

export const intelligenceApi = {
  route: (body: {
    message: string;
    mode: string;
    explicit_task?: string | null;
    manual_provider?: string | null;
    manual_model?: string | null;
    agent_id?: string | null;
    requires_tools?: boolean;
    requires_vision?: boolean;
    min_context_tokens?: number | null;
  }) => apiClient.post<RoutingDecision>("/api/v1/intelligence/route", body),
  profiles: () => apiClient.get<ModelCapabilityProfile[]>("/api/v1/intelligence/model-profiles")
};

