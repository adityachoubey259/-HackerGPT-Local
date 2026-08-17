import {
  Database,
  FileSearch,
  FolderInput,
  RefreshCcw,
  Search,
  Trash2,
  Upload
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { knowledgeApi } from "../api/knowledge";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import type { KnowledgeDocument, KnowledgeSearchResult, KnowledgeStats } from "../types/api";
import { cn, formatBytes, titleCase } from "../utils";

export function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [path, setPath] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[]>([]);
  const [selected, setSelected] = useState<KnowledgeDocument | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    const [list, nextStats] = await Promise.all([
      knowledgeApi.list({ search, limit: 50 }),
      knowledgeApi.stats()
    ]);
    setDocuments(list.items);
    setStats(nextStats);
    setSelected((current) => current ?? (list.items.length > 0 ? list.items[0] : null));
  }, [search]);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void load().catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Knowledge could not be loaded.");
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
      setError(reason instanceof Error ? reason.message : "Knowledge operation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
            Private knowledge intelligence
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Knowledge Base</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Ingest local documents, chunk them safely, retrieve grounded context, and surface
            citations without sending content to hidden cloud services.
          </p>
        </div>
        <Button
          icon={<Upload size={16} />}
          onClick={() => fileInputRef.current?.click()}
          variant="primary"
        >
          Upload
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          className="sr-only"
          onChange={(event) => {
            const file = event.currentTarget.files?.[0];
            if (file) {
              void run(async () => {
                await knowledgeApi.upload(file);
              });
            }
            event.currentTarget.value = "";
          }}
        />
      </header>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="Documents" value={stats?.document_count.toString() ?? "0"} />
        <Metric label="Chunks" value={stats?.chunk_count.toString() ?? "0"} />
        <Metric label="Embeddings" value={stats?.embedding_model ?? "local"} />
        <Metric label="Vector store" value={stats?.vector_store_status ?? "unknown"} />
      </section>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid min-h-[62vh] gap-4 xl:grid-cols-[0.95fr_1.1fr_0.95fr]">
        <Card className="p-0">
          <div className="border-b border-border-subtle p-4">
            <div className="flex items-center gap-2 rounded-xl border border-border-subtle bg-elevated/70 px-3">
              <Search size={15} className="text-muted" />
              <input
                aria-label="Search documents"
                className="h-10 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted"
                placeholder="Search indexed sources"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>
          <div className="max-h-[62vh] space-y-2 overflow-auto p-3">
            {documents.map((document) => (
              <button
                key={document.id}
                className={cn(
                  "w-full rounded-xl border p-3 text-left transition hover:bg-elevated/70",
                  selected?.id === document.id
                    ? "border-accent/40 bg-accent/10"
                    : "border-border-subtle bg-elevated/35"
                )}
                onClick={() => setSelected(document)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{document.title ?? document.name}</div>
                    <div className="mt-1 truncate text-xs text-muted">{document.name}</div>
                  </div>
                  <StatusBadge status={document.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
                  <span>{formatBytes(document.size_bytes)}</span>
                  <span>{document.parser ?? "parser pending"}</span>
                </div>
              </button>
            ))}
            {documents.length === 0 ? (
              <EmptyState title="No indexed knowledge yet" icon={<Database size={26} />}>
                Upload a document or ingest a safe local path to start building grounded context.
              </EmptyState>
            ) : null}
          </div>
        </Card>

        <Card className="space-y-4">
          <div>
            <h2 className="flex items-center gap-2 font-semibold">
              <FileSearch size={17} className="text-accent" />
              Semantic Retrieval
            </h2>
            <p className="mt-1 text-sm text-muted">
              Search indexed chunks and inspect source citations before they enter chat context.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              aria-label="Search knowledge"
              className="h-10 min-w-0 flex-1 rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm outline-none"
              placeholder="Ask a source-grounded question"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && query.trim()) {
                  void run(async () => {
                    setResults((await knowledgeApi.search(query)).items);
                  });
                }
              }}
            />
            <Button
              disabled={!query.trim() || busy}
              icon={<Search size={16} />}
              onClick={() =>
                void run(async () => {
                  setResults((await knowledgeApi.search(query)).items);
                })
              }
            >
              Search
            </Button>
          </div>
          <div className="space-y-3">
            {results.map((result) => (
              <div key={result.chunk_id} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex items-center justify-between gap-3">
                  <Badge tone="accent">{result.citation_id}</Badge>
                  <span className="text-technical text-xs text-muted">{result.score.toFixed(3)}</span>
                </div>
                <p className="mt-3 line-clamp-5 text-sm leading-6 text-secondary">{result.text}</p>
                <div className="mt-3 text-xs text-muted">
                  {result.file_name}
                  {result.page_number ? `, page ${result.page_number.toString()}` : ""}
                  {result.section ? `, ${result.section}` : ""}
                </div>
              </div>
            ))}
            {results.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-subtle p-6 text-center text-sm text-muted">
                Retrieval results will appear here with stable citation IDs.
              </div>
            ) : null}
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <FolderInput size={17} className="text-accent" />
            Source Control
          </h2>
          <div className="space-y-2">
            <input
              aria-label="Local path"
              className="h-10 w-full rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm outline-none"
              placeholder="Allowed local file or directory path"
              value={path}
              onChange={(event) => setPath(event.target.value)}
            />
            <Button
              className="w-full"
              disabled={!path.trim() || busy}
              icon={<FolderInput size={16} />}
              onClick={() =>
                void run(async () => {
                  await knowledgeApi.ingestPath(path.trim());
                  setPath("");
                })
              }
            >
              Ingest Path
            </Button>
          </div>
          {selected ? (
            <div className="space-y-3 rounded-xl border border-border-subtle bg-elevated/45 p-3">
              <div>
                <div className="text-xs uppercase text-muted">Selected document</div>
                <div className="mt-1 break-words text-sm font-semibold">{selected.title ?? selected.name}</div>
              </div>
              <Info label="Checksum" value={selected.checksum.slice(0, 16)} />
              <Info label="MIME" value={selected.mime_type ?? "Unknown"} />
              <Info label="Indexed" value={selected.indexed_at ? new Date(selected.indexed_at).toLocaleString() : "Pending"} />
              {selected.failure_message ? (
                <div className="rounded-lg border border-danger/25 bg-danger/10 p-2 text-xs text-danger">
                  {selected.failure_message}
                </div>
              ) : null}
              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  icon={<RefreshCcw size={15} />}
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      await knowledgeApi.reindex(selected.id);
                    })
                  }
                >
                  Reindex
                </Button>
                <Button
                  className="flex-1"
                  icon={<Trash2 size={15} />}
                  variant="danger"
                  disabled={busy}
                  onClick={() =>
                    void run(async () => {
                      await knowledgeApi.delete(selected.id);
                      setSelected(null);
                    })
                  }
                >
                  Delete
                </Button>
              </div>
            </div>
          ) : null}
        </Card>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="hairline-panel rounded-xl p-4">
      <div className="text-sm text-muted">{label}</div>
      <div className="mt-2 truncate text-xl font-semibold">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: KnowledgeDocument["status"] }) {
  const tone = status === "indexed" ? "positive" : status === "failed" ? "danger" : "warning";
  return <Badge tone={tone}>{titleCase(status)}</Badge>;
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 text-sm">
      <span className="text-muted">{label}</span>
      <span className="min-w-0 break-words text-right text-secondary">{value}</span>
    </div>
  );
}
