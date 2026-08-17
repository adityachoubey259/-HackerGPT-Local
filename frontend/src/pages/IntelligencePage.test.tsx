import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";
import { IntelligencePage } from "./IntelligencePage";

describe("IntelligencePage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads model profiles and renders a routing decision", async () => {
    mockFetch((url) => {
      if (url.includes("/model-profiles")) {
        return jsonResponse([
          {
            pattern: "qwen*coder*",
            strengths: ["coding", "typescript"],
            weaknesses: [],
            context_length: 32768,
            max_output_tokens: null,
            coding_score: 0.95,
            reasoning_score: 0.75,
            speed_score: 0.6,
            tool_support: null,
            vision: null,
            structured_output: true,
            recommended_agents: [],
            estimated_vram_bytes: 5200000000,
            estimated_ram_bytes: null,
            default_generation: {}
          }
        ]);
      }
      if (url.includes("/config/public")) {
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
      return jsonResponse({
        provider: "ollama",
        model: "qwen-coder",
        mode: "auto",
        task: "frontend",
        manual: false,
        candidates: [
          {
            provider: "ollama",
            model: "qwen-coder",
            display_name: "qwen-coder",
            score: 1.1,
            hardware_fit: "good",
            local: true,
            reasons: ["local provider", "task capability profile match"],
            warnings: []
          }
        ],
        diagnostics: ["task=frontend"],
        error: null
      });
    });

    renderApp(<IntelligencePage />);
    await waitFor(() => expect(screen.getByText("qwen*coder*")).toBeInTheDocument());
    expect(screen.getByText("Direct Expert")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /inspect route/i }));
    await waitFor(() => expect(screen.getByText("ollama / qwen-coder")).toBeInTheDocument());
    expect(screen.getByText("Task: Frontend")).toBeInTheDocument();
  });
});
