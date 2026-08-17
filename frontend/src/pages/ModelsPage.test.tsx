import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ModelsPage } from "./ModelsPage";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

const provider = {
  provider: "ollama",
  type: "ollama",
  status: "healthy",
  message: "Ollama is reachable.",
  capabilities: ["chat", "model_discovery"],
  base_url: "http://127.0.0.1:11434",
  details: {}
};

const model = {
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
  estimated_vram_bytes: 5200000000,
  capabilities: ["chat"],
  modified_at: null,
  loaded: true,
  suitability: "suitable",
  metadata: {}
};

describe("ModelsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders provider health and discovered models", async () => {
    mockFetch((url) => {
      if (url.includes("/providers")) {
        return jsonResponse([provider]);
      }
      return jsonResponse([model]);
    });
    renderApp(<ModelsPage />);
    await waitFor(() => expect(screen.getAllByText("qwen3:8b").length).toBeGreaterThan(0));
    expect(screen.getByText("healthy")).toBeInTheDocument();
    expect(screen.getByText("Q4_K_M")).toBeInTheDocument();
  });

  it("renders offline provider state", async () => {
    mockFetch((url) => {
      if (url.includes("/providers")) {
        return jsonResponse([{ ...provider, status: "unavailable", message: "Ollama is not reachable." }]);
      }
      return jsonResponse([]);
    });
    renderApp(<ModelsPage />);
    await waitFor(() => expect(screen.getByText("unavailable")).toBeInTheDocument());
    expect(screen.getByText("No installed models were discovered from enabled providers.")).toBeInTheDocument();
  });

  it("runs model test success and failure", async () => {
    let fail = false;
    mockFetch((url) => {
      if (url.includes("/providers")) {
        return jsonResponse([provider]);
      }
      if (url.includes("/models/test")) {
        if (fail) {
          return jsonResponse(
            {
              error: {
                code: "PROVIDER_UNAVAILABLE",
                message: "Provider offline.",
                request_id: "req-1",
                details: {}
              }
            },
            503,
            "req-1"
          );
        }
        return jsonResponse({
          provider: "ollama",
          model: "qwen3:8b",
          text: "Hello!",
          duration_ms: 10,
          usage: null,
          metrics: {
            provider: "ollama",
            model: "qwen3:8b",
            duration_ms: 10,
            prompt_tokens: null,
            completion_tokens: null,
            total_tokens: null,
            tokens_per_second: null,
            success: true
          }
        });
      }
      return jsonResponse([model]);
    });
    renderApp(<ModelsPage />);
    await waitFor(() => expect(screen.getAllByText("qwen3:8b").length).toBeGreaterThan(0));
    await userEvent.click(screen.getByRole("button", { name: /run test/i }));
    await waitFor(() => expect(screen.getByText("Hello!")).toBeInTheDocument());
    fail = true;
    await userEvent.click(screen.getByRole("button", { name: /run test/i }));
    await waitFor(() => expect(screen.getByText("PROVIDER_UNAVAILABLE")).toBeInTheDocument());
  });
});
