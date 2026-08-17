import { Bot, Brain, Copy, Database, MemoryStick, Plus, ShieldCheck, Wrench } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";

import { agentsApi } from "../api/agents";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { useAgentStore } from "../stores/agentStore";
import type { AgentDefinition } from "../types/api";
import { cn, titleCase } from "../utils";

export function AgentsPage() {
  const agents = useAgentStore((state) => state.agents);
  const selectedAgentId = useAgentStore((state) => state.selectedAgentId);
  const loadAgents = useAgentStore((state) => state.loadAgents);
  const selectAgent = useAgentStore((state) => state.selectAgent);
  const [selected, setSelected] = useState<AgentDefinition | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    await loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    void refresh().catch(() => setError("Agents could not be loaded."));
  }, [refresh]);

  useEffect(() => {
    const preferred = agents.find((agent) => agent.id === (selected?.id ?? selectedAgentId));
    setSelected(preferred ?? (agents.length > 0 ? agents[0] : null));
  }, [agents, selected?.id, selectedAgentId]);

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent operation failed.");
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
            Agent command layer
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Agents</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Select role-specific local intelligence profiles. Agent prompts are trusted
            configuration, but they remain subordinate to global policy and tool permissions.
          </p>
        </div>
        <Button icon={<Plus size={16} />} onClick={() => setCreating((value) => !value)}>
          New Custom
        </Button>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      {creating ? (
        <CreateAgentPanel
          onCreate={(body) =>
            run(async () => {
              const created = await agentsApi.create(body);
              selectAgent(created.id);
              setCreating(false);
            })
          }
        />
      ) : null}

      <section className="grid min-h-[62vh] gap-4 xl:grid-cols-[0.95fr_1.25fr]">
        <Card className="p-0">
          <div className="grid max-h-[70vh] gap-2 overflow-auto p-3">
            {agents.map((agent) => (
              <button
                key={agent.id}
                className={cn(
                  "rounded-xl border p-3 text-left transition hover:bg-elevated/70",
                  selected?.id === agent.id
                    ? "border-accent/40 bg-accent/10"
                    : "border-border-subtle bg-elevated/35"
                )}
                onClick={() => setSelected(agent)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{agent.name}</div>
                    <div className="mt-1 line-clamp-2 text-xs leading-5 text-muted">
                      {agent.description}
                    </div>
                  </div>
                  <Badge tone={agent.enabled ? "positive" : "warning"}>
                    {agent.built_in ? "Built-in" : "Custom"}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
                  <span>{agent.allowed_tools.length.toString()} tools</span>
                  <span>{titleCase(agent.context_strategy)}</span>
                  <span>{agent.rag_config.enabled ? "RAG" : "No RAG"}</span>
                  <span>{agent.memory_config.enabled ? "Memory" : "No memory"}</span>
                </div>
              </button>
            ))}
            {agents.length === 0 ? (
              <EmptyState title="No agents configured" icon={<Brain size={26} />}>
                Built-in agent configuration could not be loaded.
              </EmptyState>
            ) : null}
          </div>
        </Card>

        {selected ? (
          <AgentDetail
            agent={selected}
            active={selected.id === selectedAgentId}
            onSelect={() => selectAgent(selected.id)}
            onDuplicate={() => {
              void run(async () => void (await agentsApi.duplicate(selected.id)));
            }}
            onToggle={() => {
              void run(async () => {
                if (!selected.built_in) {
                  await agentsApi.patch(selected.id, { enabled: !selected.enabled });
                }
              });
            }}
          />
        ) : null}
      </section>
    </div>
  );
}

function AgentDetail({
  agent,
  active,
  onSelect,
  onDuplicate,
  onToggle
}: {
  agent: AgentDefinition;
  active: boolean;
  onSelect: () => void;
  onDuplicate: () => void;
  onToggle: () => void;
}) {
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{agent.name}</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">{agent.description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant={active ? "secondary" : "primary"} onClick={onSelect}>
            {active ? "Active" : "Select"}
          </Button>
          <Button icon={<Copy size={15} />} onClick={onDuplicate}>
            Duplicate
          </Button>
          {!agent.built_in ? <Button onClick={onToggle}>Toggle</Button> : null}
        </div>
      </div>
      <section className="grid gap-3 md:grid-cols-2">
        <InfoBlock icon={<Bot size={16} />} title="Model">
          <Info label="Provider" value={agent.preferred_provider ?? "User selected"} />
          <Info label="Model" value={agent.preferred_model ?? "User selected"} />
          <Info label="Temperature" value={agent.temperature.toString()} />
          <Info label="Max tokens" value={agent.max_output_tokens.toString()} />
        </InfoBlock>
        <InfoBlock icon={<Database size={16} />} title="Knowledge">
          <Info label="RAG" value={agent.rag_config.enabled ? "Enabled" : "Disabled"} />
          <Info label="Scope" value={agent.rag_config.knowledge_scope} />
          <Info label="Results" value={agent.rag_config.result_limit.toString()} />
        </InfoBlock>
        <InfoBlock icon={<MemoryStick size={16} />} title="Memory">
          <Info label="Memory" value={agent.memory_config.enabled ? "Enabled" : "Disabled"} />
          <Info label="Max memories" value={agent.memory_config.maximum_memories.toString()} />
          <Info
            label="Summaries"
            value={agent.memory_config.conversation_summaries ? "Enabled" : "Disabled"}
          />
        </InfoBlock>
        <InfoBlock icon={<Wrench size={16} />} title="Tools">
          <Info label="Allowed" value={agent.allowed_tools.length.toString()} />
          <Info label="Tool loop" value={agent.tool_execution_config.max_tool_calls.toString()} />
          <div className="mt-2 flex flex-wrap gap-2">
            {agent.allowed_tools.slice(0, 10).map((tool) => (
              <Badge key={tool} tone="neutral">
                {tool}
              </Badge>
            ))}
          </div>
        </InfoBlock>
      </section>
      <InfoBlock icon={<ShieldCheck size={16} />} title="Behavior">
        <p className="whitespace-pre-wrap text-sm leading-6 text-secondary">{agent.system_prompt}</p>
      </InfoBlock>
    </Card>
  );
}

function CreateAgentPanel({
  onCreate
}: {
  onCreate: (body: {
    name: string;
    description: string;
    system_prompt: string;
    configuration: Record<string, unknown>;
    enabled: boolean;
  }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [prompt, setPrompt] = useState("");
  return (
    <Card className="grid gap-3 md:grid-cols-[0.8fr_1fr]">
      <input
        aria-label="Agent name"
        className="h-10 rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm"
        placeholder="Agent name"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <input
        aria-label="Agent description"
        className="h-10 rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm"
        placeholder="Purpose"
        value={description}
        onChange={(event) => setDescription(event.target.value)}
      />
      <textarea
        aria-label="System prompt"
        className="min-h-28 rounded-xl border border-border-subtle bg-elevated/60 px-3 py-2 text-sm md:col-span-2"
        placeholder="Trusted custom system prompt"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
      />
      <Button
        className="md:col-span-2"
        disabled={!name.trim() || !prompt.trim()}
        onClick={() =>
          void onCreate({
            name,
            description,
            system_prompt: prompt,
            configuration: { allowed_tools: ["filesystem.read", "filesystem.search"] },
            enabled: true
          })
        }
      >
        Create Agent
      </Button>
    </Card>
  );
}

function InfoBlock({
  icon,
  title,
  children
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border-subtle bg-elevated/45 p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <span className="text-accent">{icon}</span>
        {title}
      </h3>
      {children}
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-2 flex justify-between gap-3 text-sm">
      <span className="text-muted">{label}</span>
      <span className="min-w-0 break-words text-right text-secondary">{value}</span>
    </div>
  );
}
