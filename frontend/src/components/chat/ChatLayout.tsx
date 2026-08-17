import { ArrowDown } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatComposer } from "./ChatComposer";
import { MessageList } from "./MessageList";
import { systemApi } from "../../api/system";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";
import { useConversationStore } from "../../stores/conversationStore";
import { useAgentStore } from "../../stores/agentStore";
import { useModelStore } from "../../stores/modelStore";
import { useAsyncResource } from "../../hooks/useAsyncResource";

export function ChatLayout() {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [following, setFollowing] = useState(true);
  const messages = useConversationStore((state) => state.messages);
  const runState = useConversationStore((state) => state.runState);
  const sendMessage = useConversationStore((state) => state.sendMessage);
  const stopGeneration = useConversationStore((state) => state.stopGeneration);
  const selectedProvider = useModelStore((state) => state.selectedProvider);
  const selectedModel = useModelStore((state) => state.selectedModel);
  const selectedAgentId = useAgentStore((state) => state.selectedAgentId);
  const agents = useAgentStore((state) => state.agents);
  const config = useAsyncResource(useCallback((signal) => systemApi.publicConfig(signal), []));
  const streaming = runState === "submitting" || runState === "streaming" || runState === "cancelling";
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? null;

  const scrollToBottom = (behavior: ScrollBehavior) => {
    const element = scrollRef.current;
    if (!element) {
      return;
    }
    if (typeof element.scrollTo === "function") {
      element.scrollTo({ top: element.scrollHeight, behavior });
    } else {
      element.scrollTop = element.scrollHeight;
    }
  };

  useEffect(() => {
    if (following) {
      scrollToBottom("smooth");
    }
  }, [following, messages]);

  return (
    <section className="flex h-full min-h-0 flex-col bg-[radial-gradient(circle_at_50%_0%,rgb(var(--color-accent)/0.07),transparent_34rem)]">
      <div
        className="relative flex-1 overflow-auto px-4 py-5"
        ref={scrollRef}
        onScroll={(event) => {
          const element = event.currentTarget;
          const distance = element.scrollHeight - element.scrollTop - element.clientHeight;
          setFollowing(distance < 120);
        }}
      >
        <MessageList messages={messages} />
        {!following ? (
          <Button
            className="sticky bottom-3 left-1/2 -translate-x-1/2"
            icon={<ArrowDown size={15} />}
            onClick={() => {
              setFollowing(true);
              scrollToBottom("smooth");
            }}
          >
            Jump to bottom
          </Button>
        ) : null}
      </div>
      <div className="mx-auto flex w-full max-w-4xl flex-wrap gap-2 px-4 pb-2">
        <Badge tone="accent">
          {config.data?.response.default_mode === "direct_expert" ? "Direct Expert" : "Standard"}
        </Badge>
        {selectedAgent ? <Badge>{selectedAgent.name}</Badge> : null}
        {selectedAgent?.id === "cybersecurity" ? (
          <Badge tone="positive">Active scope: app state</Badge>
        ) : null}
      </div>
      <ChatComposer
        streaming={streaming}
        onStop={() => {
          void stopGeneration();
        }}
        onSubmit={(content) => {
          void sendMessage({
            content,
            provider: selectedProvider,
            model: selectedModel,
            agentId: selectedAgentId
          });
        }}
      />
    </section>
  );
}
