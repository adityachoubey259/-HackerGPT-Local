import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ToolsPage } from "./ToolsPage";
import { useAgentStore } from "../stores/agentStore";
import type { ToolConfirmation, ToolDefinition, ToolExecution } from "../types/api";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

const tools: ToolDefinition[] = [
  {
    name: "filesystem.list",
    description: "List files safely.",
    permission_class: "READ_ONLY",
    capabilities: ["filesystem", "read"],
    input_schema: {},
    enabled: true
  },
  {
    name: "filesystem.write",
    description: "Write a file after confirmation.",
    permission_class: "WRITE_LOCAL",
    capabilities: ["filesystem", "write"],
    input_schema: {},
    enabled: true
  }
];

const history: ToolExecution[] = [
  {
    id: "exec-1",
    tool_name: "filesystem.list",
    permission_class: "READ_ONLY",
    status: "completed",
    input: { path: "." },
    working_directory: "C:/Projects/HackerGPT Local",
    command_display: null,
    stdout: "backend\nfrontend",
    stderr: null,
    exit_code: 0,
    data: {},
    error_code: null,
    error_message: null,
    truncated: false,
    duration_ms: 12,
    started_at: "2026-08-10T00:00:00Z",
    completed_at: "2026-08-10T00:00:00Z",
    created_at: "2026-08-10T00:00:00Z",
    updated_at: "2026-08-10T00:00:00Z"
  }
];

const confirmation: ToolConfirmation = {
  id: "confirm-1",
  execution_id: "exec-write",
  tool_name: "filesystem.write",
  permission_class: "WRITE_LOCAL",
  status: "pending",
  risk_summary: "Local write requires confirmation.",
  expires_at: "2026-08-10T00:05:00Z",
  created_at: "2026-08-10T00:00:00Z"
};

describe("ToolsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useAgentStore.setState({ agents: [], selectedAgentId: null, loading: false });
  });

  it("renders registry, activity, and confirmation review dialog", async () => {
    const fetchSpy = mockFetch((url, init) => {
      if (url.includes("/api/v1/tools/confirmations/confirm-1/approve")) {
        return jsonResponse({
          execution: history[0],
          confirmation: { ...confirmation, status: "approved" }
        });
      }
      if (url.includes("/api/v1/tools/execute") && init?.method === "POST") {
        return jsonResponse({
          execution: { ...history[0], id: "exec-write", status: "pending_confirmation" },
          confirmation,
          decision: "require_confirmation",
          reason: "Local write requires confirmation."
        });
      }
      if (url.includes("/api/v1/tools/confirmations")) {
        return jsonResponse([confirmation]);
      }
      if (url.includes("/api/v1/tools/executions")) {
        return jsonResponse({ items: history, total: history.length });
      }
      if (url.includes("/api/v1/tools")) {
        return jsonResponse({ items: tools });
      }
      return jsonResponse({});
    });

    useAgentStore.setState({ selectedAgentId: "coding" });
    renderApp(<ToolsPage />);
    const writeLabels = await screen.findAllByText("filesystem.write");
    const writeButton = writeLabels[0]?.closest("button");
    if (!writeButton) {
      throw new Error("Expected filesystem.write registry button.");
    }
    await userEvent.click(writeButton);
    await userEvent.click(screen.getByRole("button", { name: /request execution/i }));

    let dialog = await screen.findByRole("dialog", { name: /review tool operation/i });
    expect(within(dialog).getByText("Local write requires confirmation.")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /review/i }));
    dialog = await screen.findByRole("dialog", { name: /review tool operation/i });
    await userEvent.click(within(dialog).getByRole("button", { name: /approve once/i }));

    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/tools/confirmations/confirm-1/approve"),
        expect.objectContaining({ method: "POST" })
      )
    );
    expect(screen.getByText("Tool Activity")).toBeInTheDocument();
    expect(screen.getByText(/backend\s+frontend/)).toBeInTheDocument();
  });
});
