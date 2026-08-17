import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AgentsPage } from "./AgentsPage";
import { useAgentStore } from "../stores/agentStore";
import type { AgentDefinition } from "../types/api";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

const agents: AgentDefinition[] = [
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
  },
  {
    id: "coding",
    name: "Coding Agent",
    description: "Engineering-focused agent.",
    icon: "code",
    system_prompt: "Use senior engineering judgment.",
    preferred_provider: "ollama",
    preferred_model: "qwen2.5-coder:7b",
    temperature: 0.35,
    top_p: 0.9,
    max_output_tokens: 900,
    allowed_tools: ["filesystem.read", "git.status", "python.run"],
    memory_config: {
      enabled: true,
      memory_types: ["user", "project"],
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
    context_strategy: "code-focused",
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
];

describe("AgentsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useAgentStore.setState({ agents: [], selectedAgentId: null, loading: false });
  });

  it("shows agent detail sections and supports explicit selection", async () => {
    mockFetch((url) => {
      if (url.includes("/api/v1/agents")) {
        return jsonResponse(agents);
      }
      return jsonResponse({});
    });

    renderApp(<AgentsPage />);
    await screen.findByText("General Agent");
    await userEvent.click(screen.getByText("Coding Agent"));
    await userEvent.click(screen.getByRole("button", { name: "Select" }));

    expect(screen.getByRole("heading", { name: "Model" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Knowledge" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Memory" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Tools" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Behavior" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Active" })).toBeInTheDocument());
  });

  it("duplicates an agent through the API", async () => {
    const fetchSpy = mockFetch((url, init) => {
      if (url.includes("/api/v1/agents/coding/duplicate") && init?.method === "POST") {
        return jsonResponse({ ...agents[1], id: "coding-copy", name: "Coding Agent Copy" }, 201);
      }
      if (url.includes("/api/v1/agents")) {
        return jsonResponse(agents);
      }
      return jsonResponse({});
    });

    renderApp(<AgentsPage />);
    await screen.findByText("Coding Agent");
    await userEvent.click(screen.getByText("Coding Agent"));
    await userEvent.click(screen.getByRole("button", { name: /duplicate/i }));

    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/agents/coding/duplicate"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });
});
