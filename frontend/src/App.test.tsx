import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { App } from "./App";
import { useAuthStore } from "./stores/authStore";
import { jsonResponse, mockFetch, renderApp } from "./test/testUtils";

describe("App shell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({ status: "checking", user: null, error: null });
    window.history.pushState({}, "", "/");
  });

  it("renders chat shell and navigates to models", async () => {
    mockFetch((url) => {
      if (url.includes("/api/v1/auth/me")) {
        return jsonResponse({
          authenticated: true,
          user: {
            id: "local-user",
            username: "admin",
            display_name: "Local Admin",
            role: "admin",
            is_bootstrap: true
          }
        });
      }
      if (url.includes("/api/v1/models/providers")) {
        return jsonResponse([
          {
            provider: "ollama",
            type: "ollama",
            status: "healthy",
            message: "Ollama is reachable.",
            capabilities: ["chat", "model_discovery"],
            base_url: "http://127.0.0.1:11434",
            details: {}
          }
        ]);
      }
      if (url.includes("/api/v1/conversations")) {
        return jsonResponse({ items: [], pagination: { limit: 50, offset: 0, total: 0 } });
      }
      if (url.includes("/api/v1/agents")) {
        return jsonResponse([
          {
            id: "general",
            name: "General Agent",
            description: "Balanced local assistant.",
            icon: "sparkles",
            system_prompt: "Stay safe.",
            preferred_provider: null,
            preferred_model: null,
            temperature: 0.7,
            top_p: 0.9,
            max_output_tokens: 512,
            allowed_tools: ["filesystem.read"],
            memory_config: {
              enabled: true,
              memory_types: ["user"],
              maximum_memories: 5,
              project_memory: true,
              conversation_summaries: false
            },
            rag_config: {
              enabled: true,
              knowledge_scope: "all",
              result_limit: 5,
              reranking: false,
              source_diversity: true
            },
            context_strategy: "balanced",
            required_model_capabilities: ["streaming"],
            tool_execution_config: {
              enabled: true,
              max_tool_calls: 3,
              require_confirmation_for_write: true,
              require_confirmation_for_high_impact: true
            },
            enabled: true,
            built_in: true,
            metadata: {}
          }
        ]);
      }
      if (url.includes("/api/v1/config/public")) {
        return jsonResponse({
          environment: "test",
          debug: true,
          network_access: false,
          api: {},
          model_endpoint: {},
          response: {
            default_mode: "direct_expert",
            directness: "high",
            technical_depth: "expert",
            assume_technical_user: true,
            generic_disclaimers: false,
            moralizing: false,
            shallow_keyword_filtering: false,
            prefer_complete_code: true,
            prefer_exact_commands: true,
            verify_current_information: true,
            investigate_before_unknown: true,
            cite_retrieved_sources: true
          }
        });
      }
      if (url.includes("/api/v1/models")) {
        return jsonResponse([
          {
            id: "ollama:qwen3:8b",
            name: "qwen3:8b",
            provider: "ollama",
            provider_model_id: "qwen3:8b",
            family: "qwen3",
            architecture: null,
            parameter_count: "8B",
            quantization: "Q4_K_M",
            context_length: null,
            size_bytes: 5200000000,
            estimated_ram_bytes: null,
            estimated_vram_bytes: null,
            capabilities: ["chat"],
            modified_at: null,
            loaded: false,
            suitability: "suitable",
            metadata: {}
          }
        ]);
      }
      return jsonResponse({});
    });
    renderApp(<App />);
    await waitFor(() => expect(screen.getByText("Private AI workstation ready")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("link", { name: /models/i }));
    await waitFor(() => expect(screen.getAllByText("qwen3:8b").length).toBeGreaterThan(0));
  });
});
