import { Activity, Boxes, ChevronDown, Gauge, PanelRightClose, PanelRightOpen, Route } from "lucide-react";
import type { ReactNode } from "react";

import { IconButton } from "../ui/IconButton";
import { StatusIndicator } from "../ui/StatusIndicator";
import { useConversationStore } from "../../stores/conversationStore";
import { useModelStore } from "../../stores/modelStore";
import { useUiStore } from "../../stores/uiStore";
import { cn } from "../../utils";

export function RightInspector() {
  const collapsed = useUiStore((state) => state.inspectorCollapsed);
  const toggle = useUiStore((state) => state.toggleInspector);
  const selectedProvider = useModelStore((state) => state.selectedProvider);
  const selectedModel = useModelStore((state) => state.selectedModel);
  const providers = useModelStore((state) => state.providers);
  const runState = useConversationStore((state) => state.runState);
  const streamMeta = useConversationStore((state) => state.streamMeta);
  const streamContext = useConversationStore((state) => state.streamContext);
  const streamMetrics = useConversationStore((state) => state.streamMetrics);
  const activeGenerationId = useConversationStore((state) => state.activeGenerationId);
  const activeProvider = providers.find((provider) => provider.provider === selectedProvider);
  const sourceCount = streamContext ? streamContext.rag.length : 0;
  const memoryCount = streamContext ? streamContext.memory.length : 0;
  const topSource =
    streamContext && streamContext.rag.length > 0 ? streamContext.rag[0].file_name : "None";
  const topMemory =
    streamContext && streamContext.memory.length > 0 ? streamContext.memory[0].title : "None";

  return (
    <aside
      className={cn(
        "hidden shrink-0 border-l border-border-subtle bg-panel/90 backdrop-blur transition-[width] duration-200 ease-emphasized lg:block",
        collapsed ? "w-14" : "w-80"
      )}
    >
      <div className="flex h-16 items-center justify-between border-b border-border-subtle px-3">
        {!collapsed ? (
          <div>
            <h2 className="text-sm font-semibold">Inspector</h2>
            <p className="text-xs text-muted">Runtime context</p>
          </div>
        ) : null}
        <IconButton
          label={collapsed ? "Expand inspector" : "Collapse inspector"}
          icon={collapsed ? <PanelRightOpen size={16} /> : <PanelRightClose size={16} />}
          onClick={toggle}
        />
      </div>
      {!collapsed ? (
        <div className="space-y-3 p-3 text-sm">
          <InspectorSection icon={<Gauge size={15} />} title="Model">
            <InspectorRow label="Provider" value={selectedProvider ?? "None selected"} mono />
            <InspectorRow label="Model" value={selectedModel ?? "None selected"} mono />
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted">Runtime</span>
              {activeProvider ? (
                <StatusIndicator status={activeProvider.status} />
              ) : (
                <span className="text-xs text-muted">Unknown</span>
              )}
            </div>
          </InspectorSection>
          <InspectorSection icon={<Activity size={15} />} title="Generation">
            <InspectorRow label="Status" value={runState} />
            <InspectorRow
              label="Generation"
              value={activeGenerationId ?? streamMeta?.generation_id ?? "None"}
              mono
            />
            <InspectorRow
              label="Tokens/sec"
              value={streamMetrics?.tokens_per_second?.toFixed(1) ?? "Unknown"}
            />
            <InspectorRow
              label="TTFT"
              value={
                streamMetrics?.time_to_first_token_ms != null
                  ? `${streamMetrics.time_to_first_token_ms.toFixed(0)} ms`
                  : "Unknown"
              }
            />
            <InspectorRow
              label="Tokens"
              value={streamMetrics?.completion_tokens?.toString() ?? "Unknown"}
            />
          </InspectorSection>
          <InspectorSection icon={<Boxes size={15} />} title="Context">
            <InspectorRow
              label="Response"
              value={streamContext?.response_mode ? streamContext.response_mode.replaceAll("_", " ") : "Unknown"}
            />
            <InspectorRow
              label="Depth"
              value={streamContext?.technical_depth ?? "Unknown"}
            />
            <InspectorRow
              label="Used"
              value={streamContext ? streamContext.estimated_prompt_tokens.toString() : "Not composed"}
            />
            <InspectorRow label="Sources" value={sourceCount.toString()} />
            <InspectorRow label="Memories" value={memoryCount.toString()} />
            <div className="mt-2 h-2 rounded-full bg-elevated">
              <div
                className="h-2 rounded-full bg-accent"
                style={{
                  width: streamContext
                    ? `${Math.min(
                        100,
                        (streamContext.estimated_prompt_tokens / streamContext.context_limit) * 100
                      ).toString()}%`
                    : "0%"
                }}
              />
            </div>
          </InspectorSection>
          <InspectorSection icon={<Route size={15} />} title="Grounding">
            <InspectorRow label="Agent" value={streamContext?.agent?.name ?? "None"} />
            <InspectorRow label="RAG" value={sourceCount > 0 ? "Active" : "Idle"} />
            <InspectorRow label="Memory" value={memoryCount > 0 ? "Active" : "Idle"} />
            <InspectorRow label="Research" value="Policy-controlled" />
            <InspectorRow label="Active scope" value="Trusted app state only" />
            <InspectorRow label="Tools" value="Permission-gated" />
            <InspectorRow label="Top source" value={topSource} />
            <InspectorRow label="Top memory" value={topMemory} />
          </InspectorSection>
        </div>
      ) : null}
    </aside>
  );
}

function InspectorSection({
  icon,
  title,
  children
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border-subtle bg-elevated/50 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-xs font-semibold uppercase text-secondary">
          <span className="text-accent">{icon}</span>
          {title}
        </h3>
        <ChevronDown aria-hidden size={14} className="text-muted" />
      </div>
      <div className="space-y-2">{children}</div>
    </section>
  );
}

function InspectorRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="text-muted">{label}</span>
      <span className={cn("min-w-0 break-words text-right text-text", mono && "text-technical text-xs")}>
        {value}
      </span>
    </div>
  );
}
