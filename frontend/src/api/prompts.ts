import { apiClient } from "./client";
import type { PromptArchitectResponse, PromptProfile } from "../types/api";

export const promptsApi = {
  profiles: () => apiClient.get<PromptProfile[]>("/api/v1/prompts/profiles"),
  generate: (body: {
    objective: string;
    prompt_type: string;
    level: string;
    domain?: string | null;
    language?: string | null;
    framework?: string | null;
    output_format?: string | null;
    constraints?: string[];
    available_tools?: string[];
    use_rag?: boolean;
    use_memory?: boolean;
    use_live_research?: boolean;
    testing_required?: boolean;
    security_required?: boolean;
  }) => apiClient.post<PromptArchitectResponse>("/api/v1/prompts/generate", body)
};
