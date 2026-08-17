import { create } from "zustand";

import { chatApi } from "../api/chat";
import { conversationsApi } from "../api/conversations";
import { usePreferenceStore } from "./preferenceStore";
import type {
  ChatStreamRequest,
  Conversation,
  GenerationStatus,
  Message,
  StreamError,
  StreamContext,
  StreamMeta,
  StreamMetrics
} from "../types/api";

export type ChatRunState =
  | "idle"
  | "submitting"
  | "streaming"
  | "cancelling"
  | "completed"
  | "cancelled"
  | "failed";

interface ConversationStore {
  conversations: Conversation[];
  archivedConversations: Conversation[];
  messages: Message[];
  activeConversationId: string | null;
  search: string;
  loadingConversations: boolean;
  loadingMessages: boolean;
  runState: ChatRunState;
  activeGenerationId: string | null;
  streamMeta: StreamMeta | null;
  streamContext: StreamContext | null;
  streamMetrics: StreamMetrics | null;
  streamError: StreamError | null;
  abortController: AbortController | null;
  setSearch: (search: string) => void;
  loadConversations: (archived?: boolean) => Promise<void>;
  newChat: () => void;
  selectConversation: (conversationId: string) => Promise<void>;
  sendMessage: (input: {
    content: string;
    provider: string | null;
    model: string | null;
    agentId: string | null;
  }) => Promise<void>;
  stopGeneration: () => Promise<void>;
  renameConversation: (conversationId: string, title: string) => Promise<void>;
  archiveConversation: (conversationId: string, archived: boolean) => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  conversations: [],
  archivedConversations: [],
  messages: [],
  activeConversationId: null,
  search: "",
  loadingConversations: false,
  loadingMessages: false,
  runState: "idle",
  activeGenerationId: null,
  streamMeta: null,
  streamContext: null,
  streamMetrics: null,
  streamError: null,
  abortController: null,
  setSearch: (search) => set({ search }),
  loadConversations: async (archived = false) => {
    set({ loadingConversations: true });
    try {
      const response = await conversationsApi.list({
        archived,
        search: get().search,
        limit: 50
      });
      const items = Array.isArray(response.items) ? response.items : [];
      if (archived) {
        set({ archivedConversations: items, loadingConversations: false });
      } else {
        set({ conversations: items, loadingConversations: false });
      }
    } catch {
      set({ loadingConversations: false });
    }
  },
  newChat: () =>
    set({
      activeConversationId: null,
      messages: [],
      runState: "idle",
      streamMeta: null,
      streamContext: null,
      streamMetrics: null,
      streamError: null
    }),
  selectConversation: async (conversationId) => {
    set({ loadingMessages: true, activeConversationId: conversationId, streamError: null });
    try {
      const response = await conversationsApi.messages(conversationId, { limit: 100 });
      set({ messages: response.items, loadingMessages: false, runState: "idle" });
    } catch {
      set({ loadingMessages: false });
    }
  },
  sendMessage: async ({ content, provider, model, agentId }) => {
    const trimmed = content.trim();
    if (!trimmed || get().runState === "streaming" || get().runState === "submitting") {
      return;
    }
    const clientRequestId = crypto.randomUUID();
    const userTempId = `temp-user-${clientRequestId}`;
    const assistantTempId = `temp-assistant-${clientRequestId}`;
    const controller = new AbortController();
    const now = new Date().toISOString();
    const optimisticUser = messageDraft({
      id: userTempId,
      conversationId: get().activeConversationId ?? "pending",
      role: "user",
      content: trimmed,
      clientRequestId,
      now
    });
    const optimisticAssistant = messageDraft({
      id: assistantTempId,
      conversationId: get().activeConversationId ?? "pending",
      role: "assistant",
      content: "",
      generationStatus: "pending",
      now
    });
    set((state) => ({
      messages: [...state.messages, optimisticUser, optimisticAssistant],
      runState: "submitting",
      streamError: null,
      streamContext: null,
      streamMetrics: null,
      abortController: controller
    }));
    const request: ChatStreamRequest = {
      conversation_id: get().activeConversationId,
      client_request_id: clientRequestId,
      message: trimmed,
      provider,
      model,
      agent_id: agentId,
      settings: {
        temperature: 0.7,
        top_p: 0.9,
        max_output_tokens: 512,
        reasoning_mode: usePreferenceStore.getState().preferences?.reasoning_mode ?? "auto"
      }
    };
    try {
      for await (const event of chatApi.stream(request, controller.signal)) {
        if (event.event === "meta") {
          set((state) => ({
            activeConversationId: event.data.conversation_id,
            activeGenerationId: event.data.generation_id,
            streamMeta: event.data,
            runState: "streaming",
            messages: state.messages.map((message) => {
              if (message.id === userTempId) {
                return {
                  ...message,
                  id: event.data.user_message_id,
                  conversation_id: event.data.conversation_id
                };
              }
              if (message.id === assistantTempId) {
                return {
                  ...message,
                  id: event.data.assistant_message_id,
                  conversation_id: event.data.conversation_id,
                  generation_id: event.data.generation_id,
                  provider: event.data.provider,
                  model: event.data.model,
                  generation_status: "streaming"
                };
              }
              return message;
            })
          }));
        } else if (event.event === "delta") {
          set((state) => ({
            messages: state.messages.map((message) =>
              message.id === (state.streamMeta?.assistant_message_id ?? assistantTempId)
                ? { ...message, content: message.content + event.data.text }
                : message
            )
          }));
        } else if (event.event === "context") {
          set({ streamContext: event.data });
        } else if (event.event === "metrics") {
          set({ streamMetrics: event.data });
        } else if (event.event === "error") {
          set((state) => ({
            streamError: event.data,
            runState: "failed",
            activeGenerationId: null,
            abortController: null,
            messages: state.messages.map((message) =>
              message.id === (state.streamMeta?.assistant_message_id ?? assistantTempId)
                ? {
                    ...message,
                    content: message.content.trim() ? message.content : event.data.message,
                    generation_status: "failed",
                    finish_reason: event.data.code,
                    metadata: { ...message.metadata, error_message: event.data.message }
                  }
                : message
            )
          }));
        } else if (event.event === "done") {
          set((state) => ({
            runState: event.data.status === "cancelled" ? "cancelled" : "completed",
            activeGenerationId: null,
            abortController: null,
            messages: state.messages.map((message) =>
              message.id === event.data.assistant_message_id
                ? {
                    ...message,
                    generation_status: event.data.status,
                    finish_reason: event.data.finish_reason
                  }
                : message
            )
          }));
        }
      }
      await get().loadConversations(false);
    } catch (error) {
      const aborted = controller.signal.aborted;
      const streamError: StreamError | null = aborted
        ? null
        : {
            code: "STREAM_CLIENT_ERROR",
            message: error instanceof Error ? error.message : "Stream failed.",
            request_id: "",
            generation_id: get().activeGenerationId,
            retryable: true
          };
      set((state) => ({
        runState: aborted ? "cancelled" : "failed",
        activeGenerationId: null,
        abortController: null,
        streamError,
        messages: streamError
          ? state.messages.map((message) =>
              message.id === (state.streamMeta?.assistant_message_id ?? assistantTempId)
                ? {
                    ...message,
                    content: message.content.trim() ? message.content : streamError.message,
                    generation_status: "failed",
                    finish_reason: streamError.code,
                    metadata: { ...message.metadata, error_message: streamError.message }
                  }
                : message
            )
          : state.messages
      }));
    }
  },
  stopGeneration: async () => {
    const { activeGenerationId, abortController } = get();
    if (!activeGenerationId) {
      return;
    }
    set({ runState: "cancelling" });
    try {
      await chatApi.cancel(activeGenerationId);
    } catch {
      // Abort still closes the browser stream even if the explicit cancel endpoint races cleanup.
    } finally {
      abortController?.abort();
      set({ runState: "cancelled", activeGenerationId: null, abortController: null });
    }
  },
  renameConversation: async (conversationId, title) => {
    const updated = await conversationsApi.patch(conversationId, { title });
    set((state) => ({
      conversations: state.conversations.map((conversation) =>
        conversation.id === conversationId ? updated : conversation
      )
    }));
  },
  archiveConversation: async (conversationId, archived) => {
    await conversationsApi.patch(conversationId, { archived });
    await get().loadConversations(false);
    await get().loadConversations(true);
    if (archived && get().activeConversationId === conversationId) {
      get().newChat();
    }
  },
  deleteConversation: async (conversationId) => {
    await conversationsApi.delete(conversationId);
    await get().loadConversations(false);
    if (get().activeConversationId === conversationId) {
      get().newChat();
    }
  }
}));

function messageDraft({
  id,
  conversationId,
  role,
  content,
  now,
  clientRequestId = null,
  generationStatus = null
}: {
  id: string;
  conversationId: string;
  role: "user" | "assistant";
  content: string;
  now: string;
  clientRequestId?: string | null;
  generationStatus?: GenerationStatus | null;
}): Message {
  return {
    id,
    conversation_id: conversationId,
    role,
    content,
    metadata: {},
    client_request_id: clientRequestId,
    generation_id: null,
    generation_status: generationStatus,
    provider: null,
    model: null,
    finish_reason: null,
    prompt_tokens: null,
    completion_tokens: null,
    total_tokens: null,
    time_to_first_token_ms: null,
    duration_ms: null,
    tokens_per_second: null,
    created_at: now,
    updated_at: now
  };
}
