import { screen, waitFor } from "@testing-library/react";

import { SystemStatusPage } from "./SystemStatusPage";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

describe("SystemStatusPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders hardware and provider status", async () => {
    mockFetch((url) => {
      if (url.includes("/system/info")) {
        return jsonResponse({
          application_version: "0.1.0",
          environment: "test",
          python_version: "3.12.10",
          operating_system: "Windows",
          architecture: "AMD64",
          hostname: "local",
          database_type: "sqlite+aiosqlite",
          debug: true,
          uptime_seconds: 1
        });
      }
      if (url.includes("/system/hardware")) {
        return jsonResponse({
          operating_system: "Windows",
          os_release: "11",
          architecture: "AMD64",
          cpu: { model: "Intel", physical_cores: null, logical_processors: 16 },
          memory: { total_bytes: 17179869184, available_bytes: 8589934592 },
          gpus: [
            {
              name: "RTX 4050",
              vendor: "NVIDIA",
              vram_total_bytes: 6442450944,
              vram_free_bytes: 4294967296,
              driver_version: "610.62",
              cuda_driver_version: null,
              compute_capability: "8.9"
            }
          ],
          acceleration: {
            cuda_available: true,
            cuda_driver_version: null,
            cuda_toolkit_available: false,
            rocm_available: false,
            apple_metal_supported: false
          },
          disks: [],
          detection_warnings: []
        });
      }
      if (url.includes("/system/knowledge-memory")) {
        return jsonResponse({
          rag: {
            document_count: 2,
            chunk_count: 24,
            embedding_provider: "local",
            embedding_model: "local-hash-128",
            vector_store: "faiss",
            vector_store_status: "ready"
          },
          memory: {
            enabled: true,
            memory_count: 4,
            semantic_store_status: "ready"
          }
        });
      }
      return jsonResponse([
        {
          provider: "ollama",
          type: "ollama",
          status: "healthy",
          message: "ok",
          capabilities: [],
          base_url: "http://127.0.0.1:11434",
          details: {}
        }
      ]);
    });
    renderApp(<SystemStatusPage />);
    await waitFor(() => expect(screen.getByText("RTX 4050")).toBeInTheDocument());
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
    expect(screen.getByText("healthy")).toBeInTheDocument();
  });
});
