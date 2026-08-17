import { vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  stream: vi.fn(),
  listConversations: vi.fn()
}));

vi.mock("../api/chat", () => ({
  chatApi: {
    stream: apiMocks.stream,
    cancel: vi.fn()
  }
}));

vi.mock("../api/conversations", () => ({
  conversationsApi: {
    list: apiMocks.listConversations,
    messages: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn()
  }
}));

import { useConversationStore } from "./conversationStore";
import { useModelStore } from "./modelStore";
import { useThemeStore } from "./themeStore";
import { useUiStore } from "./uiStore";

describe("stores", () => {
  beforeEach(() => {
    apiMocks.stream.mockReset();
    apiMocks.listConversations.mockResolvedValue({ items: [], pagination: { limit: 50, offset: 0, total: 0 } });
    useConversationStore.setState({
      conversations: [],
      archivedConversations: [],
      messages: [],
      activeConversationId: null,
      runState: "idle",
      activeGenerationId: null,
      streamMeta: null,
      streamContext: null,
      streamMetrics: null,
      streamError: null,
      abortController: null
    });
  });

  it("updates model selection", () => {
    useModelStore.getState().selectModel("ollama", "qwen3:8b");
    expect(useModelStore.getState().selectedProvider).toBe("ollama");
    expect(useModelStore.getState().selectedModel).toBe("qwen3:8b");
  });

  it("toggles panels", () => {
    const initial = useUiStore.getState().sidebarCollapsed;
    useUiStore.getState().toggleSidebar();
    expect(useUiStore.getState().sidebarCollapsed).toBe(!initial);
  });

  it("applies theme preference", () => {
    useThemeStore.getState().setPreference("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    useThemeStore.getState().setPreference("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("renders provider empty stream errors into the assistant message", async () => {
    apiMocks.stream.mockImplementation(emptyProviderErrorStream);

    await useConversationStore.getState().sendMessage({
      content: "Give me a visible answer.",
      provider: "fake",
      model: "fake-model",
      agentId: null
    });

    const assistant = useConversationStore
      .getState()
      .messages.find((message) => message.role === "assistant");
    expect(assistant?.content).toBe("Provider completed without visible assistant content.");
    expect(assistant?.generation_status).toBe("failed");
    expect(useConversationStore.getState().streamError?.code).toBe("provider_empty_response");
  });
});

async function* emptyProviderErrorStream() {
  await Promise.resolve();
  yield {
    event: "error",
    data: {
      code: "provider_empty_response",
      message: "Provider completed without visible assistant content.",
      request_id: "req-1",
      generation_id: "gen-1",
      retryable: true
    }
  };
}
