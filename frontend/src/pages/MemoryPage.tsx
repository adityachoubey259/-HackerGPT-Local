import { Brain, Download, Pin, Plus, Search, ShieldCheck, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { memoryApi } from "../api/memory";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import type { MemoryItem, MemoryType } from "../types/api";
import { titleCase } from "../utils";

export function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [search, setSearch] = useState("");
  const [type, setType] = useState<MemoryType | "">("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [importance, setImportance] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const response = await memoryApi.list({ search, memoryType: type || undefined, limit: 80 });
    setItems(response.items);
  }, [search, type]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load().catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Memory could not be loaded.");
      });
    }, 160);
    return () => window.clearTimeout(handle);
  }, [load]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Memory operation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="max-w-3xl">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
          Local long-term memory
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Memory</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Store user-confirmed facts, project preferences, and conversation summaries with explicit
          provenance. Memory is local data and never becomes trusted system instruction.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[0.85fr_1.35fr]">
        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <Plus size={17} className="text-accent" />
            Save Explicit Memory
          </h2>
          <input
            aria-label="Memory title"
            className="h-10 w-full rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm outline-none"
            placeholder="Title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <textarea
            aria-label="Memory content"
            className="min-h-36 w-full resize-y rounded-xl border border-border-subtle bg-elevated/60 px-3 py-2 text-sm leading-6 outline-none"
            placeholder="User-confirmed memory content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
          <label className="block text-sm">
            <span className="text-muted">Importance</span>
            <input
              className="mt-2 w-full accent-accent"
              type="range"
              min={1}
              max={5}
              value={importance}
              onChange={(event) => setImportance(Number(event.target.value))}
            />
          </label>
          <Button
            className="w-full"
            icon={<ShieldCheck size={16} />}
            variant="primary"
            disabled={!title.trim() || !content.trim() || busy}
            onClick={() =>
              void run(async () => {
                await memoryApi.create({
                  memory_type: "user",
                  scope: "user",
                  title,
                  content,
                  importance,
                  pinned: false,
                  enabled: true,
                  tags: []
                });
                setTitle("");
                setContent("");
                setImportance(3);
              })
            }
          >
            Save to Memory
          </Button>
          <div className="rounded-xl border border-border-subtle bg-elevated/45 p-3 text-xs leading-5 text-muted">
            Automatic memory creation from model output and documents remains disabled. Save only
            facts you intentionally want retained.
          </div>
        </Card>

        <Card className="p-0">
          <div className="border-b border-border-subtle p-4">
            <div className="flex flex-wrap gap-2">
              <div className="flex min-w-64 flex-1 items-center gap-2 rounded-xl border border-border-subtle bg-elevated/70 px-3">
                <Search size={15} className="text-muted" />
                <input
                  aria-label="Search memory"
                  className="h-10 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
                  placeholder="Search remembered facts"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </div>
              <select
                aria-label="Memory type"
                className="h-10 rounded-xl border border-border-subtle bg-elevated/70 px-3 text-sm"
                value={type}
                onChange={(event) => setType(event.target.value as MemoryType | "")}
              >
                <option value="">All types</option>
                <option value="user">User</option>
                <option value="project">Project</option>
                <option value="conversation_summary">Conversation summary</option>
              </select>
              <Button
                icon={<Download size={16} />}
                onClick={() =>
                  void run(async () => {
                    await memoryApi.export();
                  })
                }
              >
                Export
              </Button>
            </div>
          </div>
          <div className="grid max-h-[70vh] gap-3 overflow-auto p-4 lg:grid-cols-2">
            {items.map((memory) => (
              <MemoryCard
                key={memory.id}
                memory={memory}
                busy={busy}
                onRun={run}
              />
            ))}
            {items.length === 0 ? (
              <div className="lg:col-span-2">
                <EmptyState title="No long-term memory yet" icon={<Brain size={26} />}>
                  Save an explicit fact or preference to make future chats more personal and local.
                </EmptyState>
              </div>
            ) : null}
          </div>
        </Card>
      </section>
    </div>
  );
}

function MemoryCard({
  memory,
  busy,
  onRun
}: {
  memory: MemoryItem;
  busy: boolean;
  onRun: (action: () => Promise<void>) => Promise<void>;
}) {
  return (
    <article className="rounded-xl border border-border-subtle bg-elevated/45 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="break-words text-sm font-semibold">{memory.title}</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone={memory.enabled ? "positive" : "warning"}>{titleCase(memory.memory_type)}</Badge>
            <Badge tone={memory.pinned ? "accent" : "neutral"}>{memory.pinned ? "Pinned" : titleCase(memory.scope)}</Badge>
          </div>
        </div>
        <span className="text-technical text-xs text-muted">I{memory.importance}</span>
      </div>
      <p className="mt-4 line-clamp-6 text-sm leading-6 text-secondary">{memory.content}</p>
      <div className="mt-4 grid gap-1 text-xs text-muted">
        <span>Source: {memory.source}</span>
        <span>Updated: {new Date(memory.updated_at).toLocaleString()}</span>
        <span>Expires: {memory.expires_at ? new Date(memory.expires_at).toLocaleDateString() : "Never"}</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          disabled={busy}
          icon={<Pin size={14} />}
          onClick={() =>
            void onRun(async () => {
              await memoryApi.patch(memory.id, { pinned: !memory.pinned });
            })
          }
        >
          {memory.pinned ? "Unpin" : "Pin"}
        </Button>
        <Button
          disabled={busy}
          onClick={() =>
            void onRun(async () => {
              await memoryApi.patch(memory.id, { enabled: !memory.enabled });
            })
          }
        >
          {memory.enabled ? "Disable" : "Enable"}
        </Button>
        <Button
          disabled={busy}
          icon={<Trash2 size={14} />}
          variant="danger"
          onClick={() =>
            void onRun(async () => {
              await memoryApi.delete(memory.id);
            })
          }
        >
          Delete
        </Button>
      </div>
    </article>
  );
}
