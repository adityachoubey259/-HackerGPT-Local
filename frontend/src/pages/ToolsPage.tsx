import { Check, Clock, Play, ShieldAlert, Terminal, Wrench, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { toolsApi } from "../api/tools";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { useAgentStore } from "../stores/agentStore";
import type { ToolConfirmation, ToolDefinition, ToolExecution } from "../types/api";
import { titleCase } from "../utils";

export function ToolsPage() {
  const selectedAgentId = useAgentStore((state) => state.selectedAgentId);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [history, setHistory] = useState<ToolExecution[]>([]);
  const [confirmations, setConfirmations] = useState<ToolConfirmation[]>([]);
  const [selectedTool, setSelectedTool] = useState("filesystem.list");
  const [argumentsText, setArgumentsText] = useState('{"path":"."}');
  const [error, setError] = useState<string | null>(null);
  const [activeConfirmationId, setActiveConfirmationId] = useState<string | null>(null);

  const selected = useMemo(
    () => {
      const preferred = tools.find((tool) => tool.name === selectedTool);
      return preferred ?? (tools.length > 0 ? tools[0] : null);
    },
    [selectedTool, tools]
  );
  const activeConfirmation = useMemo(
    () => confirmations.find((item) => item.id === activeConfirmationId) ?? null,
    [activeConfirmationId, confirmations]
  );

  const load = useCallback(async () => {
    const [nextTools, nextHistory, nextConfirmations] = await Promise.all([
      toolsApi.list(),
      toolsApi.history(),
      toolsApi.confirmations()
    ]);
    setTools(nextTools);
    setHistory(nextHistory.items);
    setConfirmations(nextConfirmations.filter((item) => item.status === "pending"));
    if (!selectedTool && nextTools[0]) {
      setSelectedTool(nextTools[0].name);
    }
  }, [selectedTool]);

  useEffect(() => {
    void load().catch(() => setError("Tool state could not be loaded."));
  }, [load]);

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Tool operation failed.");
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="max-w-3xl">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
          Secure execution fabric
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Tools</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Every tool request passes through registry lookup, schema validation, agent allowlists,
          policy classification, confirmation when needed, and persisted audit history.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[0.85fr_1.25fr_1fr]">
        <Card className="p-0">
          <div className="border-b border-border-subtle p-4">
            <h2 className="flex items-center gap-2 font-semibold">
              <Wrench size={17} className="text-accent" />
              Registry
            </h2>
          </div>
          <div className="max-h-[64vh] space-y-2 overflow-auto p-3">
            {tools.map((tool) => (
              <button
                key={tool.name}
                className="w-full rounded-xl border border-border-subtle bg-elevated/45 p-3 text-left transition hover:bg-elevated/75"
                onClick={() => {
                  setSelectedTool(tool.name);
                  setArgumentsText(defaultArgs(tool.name));
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">{tool.name}</div>
                    <div className="mt-1 line-clamp-2 text-xs leading-5 text-muted">
                      {tool.description}
                    </div>
                  </div>
                  <Badge tone={permissionTone(tool.permission_class)}>{tool.permission_class}</Badge>
                </div>
              </button>
            ))}
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <Play size={17} className="text-accent" />
            Manual Execution
          </h2>
          {selected !== null ? (
            <>
              <div className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={permissionTone(selected.permission_class)}>
                    {selected.permission_class}
                  </Badge>
                  <span className="text-sm font-medium">{selected.name}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">{selected.description}</p>
              </div>
              <textarea
                aria-label="Tool arguments"
                className="min-h-40 rounded-xl border border-border-subtle bg-elevated/60 px-3 py-2 font-mono text-xs leading-5"
                value={argumentsText}
                onChange={(event) => setArgumentsText(event.target.value)}
              />
              <Button
                icon={<Play size={16} />}
                onClick={() =>
                  void run(async () => {
                    const response = await toolsApi.execute({
                      tool_name: selected.name,
                      arguments: JSON.parse(argumentsText) as Record<string, unknown>,
                      agent_id: selectedAgentId
                    });
                    if (response.confirmation) {
                      setActiveConfirmationId(response.confirmation.id);
                    }
                  })
                }
              >
                Request Execution
              </Button>
            </>
          ) : (
            <EmptyState title="No tools registered" icon={<Wrench size={26} />}>
              Tool registry is empty.
            </EmptyState>
          )}
        </Card>

        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <ShieldAlert size={17} className="text-accent" />
            Confirmations
          </h2>
          <div className="space-y-2">
            {confirmations.map((confirmation) => (
              <div
                key={confirmation.id}
                className="rounded-xl border border-warning/30 bg-warning/10 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">{confirmation.tool_name}</div>
                    <div className="mt-1 text-xs text-muted">{confirmation.risk_summary}</div>
                  </div>
                  <Badge tone={permissionTone(confirmation.permission_class)}>
                    {confirmation.permission_class}
                  </Badge>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button
                    className="flex-1"
                    icon={<ShieldAlert size={14} />}
                    onClick={() => setActiveConfirmationId(confirmation.id)}
                  >
                    Review
                  </Button>
                  <Button
                    className="flex-1"
                    icon={<X size={14} />}
                    onClick={() => void run(async () => void (await toolsApi.deny(confirmation.id)))}
                  >
                    Cancel
                  </Button>
                  <Button
                    className="flex-1"
                    variant="primary"
                    icon={<Check size={14} />}
                    onClick={() =>
                      void run(async () => void (await toolsApi.approve(confirmation.id)))
                    }
                  >
                    Approve once
                  </Button>
                </div>
              </div>
            ))}
            {confirmations.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-subtle p-4 text-sm text-muted">
                No pending confirmations.
              </div>
            ) : null}
          </div>
        </Card>
      </section>

      <Card className="p-0">
        <div className="border-b border-border-subtle p-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <Clock size={17} className="text-accent" />
            Tool Activity
          </h2>
        </div>
        <div className="grid gap-3 p-4 lg:grid-cols-2">
          {history.map((execution) => (
            <ExecutionRow key={execution.id} execution={execution} />
          ))}
          {history.length === 0 ? (
            <EmptyState title="No tool executions yet" icon={<Terminal size={26} />}>
              Manual execution and confirmed tool calls will appear here.
            </EmptyState>
          ) : null}
        </div>
      </Card>
      {activeConfirmation ? (
        <ConfirmationDialog
          confirmation={activeConfirmation}
          onClose={() => setActiveConfirmationId(null)}
          onDeny={() =>
            void run(async () => {
              await toolsApi.deny(activeConfirmation.id);
              setActiveConfirmationId(null);
            })
          }
          onApprove={() =>
            void run(async () => {
              await toolsApi.approve(activeConfirmation.id);
              setActiveConfirmationId(null);
            })
          }
        />
      ) : null}
    </div>
  );
}

function ConfirmationDialog({
  confirmation,
  onClose,
  onDeny,
  onApprove
}: {
  confirmation: ToolConfirmation;
  onClose: () => void;
  onDeny: () => void;
  onApprove: () => void;
}) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/70 p-4 backdrop-blur-sm">
      <section
        aria-labelledby="tool-confirmation-title"
        aria-modal="true"
        className="w-full max-w-lg rounded-2xl border border-border bg-panel p-5 shadow-2xl"
        role="dialog"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-warning">
              Confirmation required
            </div>
            <h2 id="tool-confirmation-title" className="mt-2 text-xl font-semibold">
              Review tool operation
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              Approve only if the tool, permission class, and risk summary match the operation you
              intended to run.
            </p>
          </div>
          <button
            aria-label="Close confirmation"
            className="rounded-lg border border-border-subtle p-2 text-muted transition hover:bg-elevated hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onClose}
          >
            <X size={16} />
          </button>
        </div>
        <dl className="mt-5 grid gap-3 rounded-xl border border-border-subtle bg-elevated/45 p-4 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Tool</dt>
            <dd className="min-w-0 break-words text-right font-medium">{confirmation.tool_name}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Permission</dt>
            <dd>
              <Badge tone={permissionTone(confirmation.permission_class)}>
                {confirmation.permission_class}
              </Badge>
            </dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Execution</dt>
            <dd className="font-mono text-xs text-secondary">{confirmation.execution_id}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted">Expires</dt>
            <dd className="text-secondary">{new Date(confirmation.expires_at).toLocaleString()}</dd>
          </div>
          <div>
            <dt className="text-muted">Risk summary</dt>
            <dd className="mt-1 leading-6 text-secondary">{confirmation.risk_summary}</dd>
          </div>
        </dl>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button icon={<X size={14} />} onClick={onDeny}>
            Cancel
          </Button>
          <Button variant="primary" icon={<Check size={14} />} onClick={onApprove}>
            Approve once
          </Button>
        </div>
      </section>
    </div>
  );
}

function ExecutionRow({ execution }: { execution: ToolExecution }) {
  return (
    <article className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{execution.tool_name}</div>
          <div className="mt-1 text-xs text-muted">
            {execution.command_display ?? "Structured call"}
          </div>
        </div>
        <Badge tone={statusTone(execution.status)}>{titleCase(execution.status)}</Badge>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-3">
        <span>Exit: {execution.exit_code?.toString() ?? "n/a"}</span>
        <span>{execution.duration_ms?.toFixed(0) ?? "0"} ms</span>
        <span>{execution.truncated ? "Truncated" : "Full output"}</span>
      </div>
      {execution.stdout ?? execution.stderr ? (
        <pre className="mt-3 max-h-48 overflow-auto rounded-lg bg-background/70 p-3 text-xs leading-5 text-secondary">
          {execution.stdout ?? execution.stderr}
        </pre>
      ) : null}
      {execution.error_message ? (
        <div className="mt-3 rounded-lg border border-danger/25 bg-danger/10 p-2 text-xs text-danger">
          {execution.error_message}
        </div>
      ) : null}
    </article>
  );
}

function defaultArgs(toolName: string): string {
  if (toolName === "terminal.run") {
    return '{"argv":["python","--version"],"cwd":"."}';
  }
  if (toolName === "python.run") {
    return '{"code":"print(2 + 2)","cwd":"."}';
  }
  if (toolName === "filesystem.write") {
    return '{"path":"data/tool-test.txt","content":"hello"}';
  }
  if (toolName === "filesystem.search") {
    return '{"path":".","query":"HackerGPT"}';
  }
  return '{"path":"."}';
}

function permissionTone(permission: string): "neutral" | "warning" | "danger" | "accent" {
  if (permission === "READ_ONLY") {
    return "neutral";
  }
  if (permission === "WRITE_LOCAL") {
    return "warning";
  }
  if (permission === "HIGH_IMPACT") {
    return "danger";
  }
  return "accent";
}

function statusTone(status: string): "neutral" | "positive" | "warning" | "danger" {
  if (status === "completed") {
    return "positive";
  }
  if (status === "failed" || status === "timed_out" || status === "denied") {
    return "danger";
  }
  if (status === "pending_confirmation" || status === "running") {
    return "warning";
  }
  return "neutral";
}
