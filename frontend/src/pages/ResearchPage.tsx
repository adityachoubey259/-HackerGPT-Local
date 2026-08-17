import { BookOpenCheck, Globe2, LockKeyhole, Search, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { researchApi } from "../api/research";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import type { ResearchSession, ResearchSource, ResearchStatus } from "../types/api";
import { titleCase } from "../utils";

export function ResearchPage() {
  const [status, setStatus] = useState<ResearchStatus | null>(null);
  const [history, setHistory] = useState<ResearchSession[]>([]);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [answer, setAnswer] = useState("");
  const [query, setQuery] = useState("latest FastAPI security release notes");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const [nextStatus, nextHistory] = await Promise.all([
      researchApi.status(),
      researchApi.history()
    ]);
    setStatus(nextStatus);
    setHistory(nextHistory.items);
  }, []);

  useEffect(() => {
    void load().catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Research state could not be loaded.");
    });
  }, [load]);

  async function runResearch() {
    setBusy(true);
    setError(null);
    try {
      const response = await researchApi.run({
        query: query.trim(),
        max_results: status?.max_results ?? 8,
        official_only: false
      });
      setAnswer(response.session.answer);
      setSources(response.sources);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Research request failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
            Technical intelligence
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Live Research</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Query policy-approved web sources, keep citations auditable, and cache retrieved pages
            without treating source content as trusted instructions.
          </p>
        </div>
        <Badge tone={status?.enabled ? "positive" : "warning"}>
          {status?.enabled ? "Network enabled" : "Policy offline"}
        </Badge>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="Provider" value={status?.provider ?? "unknown"} />
        <Metric label="Search" value={status?.search_enabled ? "Enabled" : "Disabled"} />
        <Metric label="Max results" value={status?.max_results.toString() ?? "0"} />
        <Metric label="Cache TTL" value={`${String(status?.cache_ttl_seconds ?? 0)}s`} />
      </section>

      <section className="grid min-h-[62vh] gap-4 xl:grid-cols-[1.2fr_1fr_0.85fr]">
        <Card className="space-y-4">
          <div>
            <h2 className="flex items-center gap-2 font-semibold">
              <Search size={17} className="text-accent" />
              Research Run
            </h2>
            <p className="mt-1 text-sm text-muted">
              Disabled policy returns an explicit offline session instead of fabricated sources.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              aria-label="Research query"
              className="h-10 min-w-0 flex-1 rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && query.trim() && !busy) {
                  void runResearch();
                }
              }}
            />
            <Button
              disabled={busy || !query.trim()}
              icon={<Globe2 size={16} />}
              variant="primary"
              onClick={() => void runResearch()}
            >
              Run
            </Button>
          </div>
          {answer ? (
            <div className="rounded-xl border border-border-subtle bg-elevated/45 p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                <BookOpenCheck size={16} className="text-accent" />
                Answer Draft
              </div>
              <pre className="whitespace-pre-wrap break-words text-sm leading-6 text-secondary">
                {answer}
              </pre>
            </div>
          ) : (
            <EmptyState title="No research run selected" icon={<BookOpenCheck size={26} />}>
              Run a query to create an auditable session with citations.
            </EmptyState>
          )}
          <div className="space-y-3">
            {sources.map((source) => (
              <article key={source.id} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{source.title}</div>
                    <div className="mt-1 break-all font-mono text-xs text-muted">{source.url}</div>
                  </div>
                  <Badge tone="accent">{source.citation_id}</Badge>
                </div>
                <p className="mt-3 line-clamp-4 text-sm leading-6 text-secondary">
                  {source.excerpt || "No excerpt returned."}
                </p>
              </article>
            ))}
          </div>
        </Card>

        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <ShieldCheck size={17} className="text-accent" />
            Source Policy
          </h2>
          <PolicyRow label="Configured" value={status?.configured ? "Yes" : "No"} />
          <PolicyRow
            label="Private networks"
            value={status?.private_networks_blocked ? "Blocked" : "Allowed"}
          />
          <PolicyRow
            label="Official preference"
            value={status?.official_sources_preferred ? "On" : "Off"}
          />
          <div>
            <div className="text-sm text-muted">Allowed domains</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(status?.allowed_domains.length ? status.allowed_domains : ["No allowlist"]).map((item) => (
                <Badge key={item}>{item}</Badge>
              ))}
            </div>
          </div>
          <div>
            <div className="text-sm text-muted">Blocked domains</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(status?.blocked_domains.length ? status.blocked_domains : ["None configured"]).map((item) => (
                <Badge key={item} tone="warning">{item}</Badge>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-warning/30 bg-warning/10 p-3 text-sm leading-6 text-warning">
            Research results are citations and data only. They cannot authorize scope, execute
            commands, change settings, or trigger tools.
          </div>
        </Card>

        <Card className="p-0">
          <div className="border-b border-border-subtle p-4">
            <h2 className="flex items-center gap-2 font-semibold">
              <LockKeyhole size={17} className="text-accent" />
              History
            </h2>
          </div>
          <div className="max-h-[62vh] space-y-2 overflow-auto p-3">
            {history.map((session) => (
              <div key={session.id} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="line-clamp-2 text-sm font-semibold">{session.query}</div>
                  <Badge tone={session.status === "completed" ? "positive" : "neutral"}>
                    {titleCase(session.status)}
                  </Badge>
                </div>
                <div className="mt-2 text-xs text-muted">
                  {new Date(session.updated_at).toLocaleString()}
                </div>
              </div>
            ))}
            {history.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-subtle p-4 text-sm text-muted">
                Research sessions will appear here.
              </div>
            ) : null}
          </div>
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

function PolicyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-elevated/45 p-3">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  );
}
