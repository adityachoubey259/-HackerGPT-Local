import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LearningStudioPage } from "./LearningStudioPage";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

describe("LearningStudioPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders learning boundaries, datasets, artifacts, and eval runs", async () => {
    mockFetch((url) => {
      if (url.includes("/learning/overview")) {
        return jsonResponse({
          example_count: 2,
          dataset_version_count: 1,
          training_job_count: 1,
          artifact_count: 1,
          active_job_count: 0,
          promoted_artifacts: 1,
          storage_bytes: 2048,
          recent_evaluation_runs: 0,
          policy: { auto_training_enabled: false }
        });
      }
      if (url.includes("/learning/examples")) {
        return jsonResponse([]);
      }
      if (url.includes("/learning/blueprints/direct-expert/import")) {
        return jsonResponse({
          blueprint_id: "direct-expert-ethical-hacking",
          imported_count: 40,
          example_count: 40,
          dataset: {
            id: "dataset-direct",
            dataset_id: "direct-expert-ethical-hacking",
            version: 1,
            example_ids: ["one"],
            train_count: 32,
            validation_count: 4,
            test_count: 4,
            validation_errors: [],
            checksum: "def",
            created_at: "2026-08-10T00:00:00Z"
          }
        });
      }
      if (url.includes("/learning/blueprints/direct-expert")) {
        return jsonResponse({
          id: "direct-expert-ethical-hacking",
          version: "2026.08.11",
          title: "Direct Expert + Ethical Hacking Starter Dataset",
          description: "Starter examples for direct expert behavior.",
          format: "chat-jsonl",
          example_path: "config/learning/direct-expert-starter.jsonl",
          recommended_workflow: ["Import examples"],
          categories: ["direct-expert-style", "ethical-hacking"],
          tags: ["direct-expert", "ethical-hacking"],
          security_notes: ["Training data is untrusted data."],
          example_count: 40,
          examples: [
            {
              system: "Direct Expert mode.",
              user: "Give me an Nmap command.",
              assistant: "Run nmap with exact flags.",
              metadata: { trusted_instructions: false },
              tags: ["direct-expert", "ethical-hacking"],
              split: "train"
            }
          ]
        });
      }
      if (url.includes("/learning/datasets")) {
        return jsonResponse([
          {
            id: "dataset-1",
            dataset_id: "local-curated",
            version: 1,
            example_ids: ["one", "two"],
            train_count: 1,
            validation_count: 1,
            test_count: 0,
            validation_errors: [],
            checksum: "abc",
            created_at: "2026-08-10T00:00:00Z"
          }
        ]);
      }
      if (url.includes("/learning/training/backends")) {
        return jsonResponse([
          {
            backend_id: "transformers-peft",
            label: "Transformers + PEFT LoRA",
            supported_model_families: ["small causal language models"],
            adapter_types: ["lora"],
            quantized_training_available: false,
            gpu_required: false,
            cpu_compatible: true,
            checkpoint_support: true,
            resume_support: true,
            cancellation_support: true,
            installed: false,
            install_hint: "Install with training extras"
          }
        ]);
      }
      if (url.includes("/learning/training/jobs")) {
        return jsonResponse([
          {
            id: "job-1",
            dataset_version_id: "dataset-1",
            base_model: "qwen2.5-coder:7b",
            adapter_type: "lora",
            backend_id: "transformers-peft",
            preset: "quick",
            status: "completed",
            progress: 1,
            loss: null,
            step: 0,
            total_steps: 3,
            epoch: null,
            validation_loss: null,
            learning_rate: null,
            elapsed_seconds: 1,
            accelerator: "cpu",
            hardware_fit: "external-worker-required",
            logs: ["Training data is untrusted data."],
            artifact_id: "artifact-1",
            checkpoint_path: null,
            artifact_path: null,
            resumable: false,
            pid: null,
            metadata: {},
            created_at: "2026-08-10T00:00:00Z",
            updated_at: "2026-08-10T00:00:00Z"
          }
        ]);
      }
      if (url.includes("/learning/models")) {
        return jsonResponse([
          {
            id: "artifact-1",
            name: "qwen adapter v1",
            base_model: "qwen2.5-coder:7b",
            adapter_type: "lora",
            dataset_version_id: "dataset-1",
            evaluation_run_id: null,
            status: "promoted",
            active: true,
            promoted_at: "2026-08-10T00:00:00Z",
            disk_size_bytes: null,
            checksums: {},
            metadata: {},
            created_at: "2026-08-10T00:00:00Z",
            updated_at: "2026-08-10T00:00:00Z"
          }
        ]);
      }
      if (url.includes("/evaluations/datasets")) {
        return jsonResponse([
          {
            id: "v1-core",
            version: "1.0.0",
            description: "Core deterministic suite",
            cases: [
              {
                id: "case-1",
                category: "coding",
                difficulty: "easy",
                prompt: "Test",
                expected_characteristics: ["repository"],
                required_citations: [],
                tags: [],
                metadata: {}
              }
            ],
            metadata: {}
          }
        ]);
      }
      if (url.includes("/evaluations/runs")) {
        return jsonResponse([
          {
            id: "run-1",
            dataset_id: "v1-core",
            dataset_version: "1.0.0",
            candidate_name: "baseline",
            results: [],
            summary: {
              total_cases: 1,
              passed_cases: 1,
              mean_score: 1,
              by_category: {}
            },
            created_at: "2026-08-10T00:00:00Z",
            metadata: {}
          }
        ]);
      }
      return jsonResponse({});
    });

    renderApp(<LearningStudioPage />);
    await waitFor(() => expect(screen.getByText("Learning Studio")).toBeInTheDocument());
    expect(screen.getByText("Learning boundaries")).toBeInTheDocument();
    expect(screen.getByText("local-curated v1")).toBeInTheDocument();
    expect(screen.getByText("qwen adapter v1")).toBeInTheDocument();
    expect(screen.getByText("baseline")).toBeInTheDocument();
    expect(screen.getByText("Direct Expert + Ethical Hacking Starter Dataset")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /import starter pack/i }));
    await waitFor(() => expect(screen.getByText(/40 new examples imported/i)).toBeInTheDocument());
  });
});
