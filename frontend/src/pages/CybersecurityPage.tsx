import {
  Activity,
  AlertTriangle,
  Crosshair,
  FileSearch,
  NotebookPen,
  Radar,
  ShieldCheck
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { securityApi } from "../api/security";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import type {
  SecurityDashboard,
  SecurityFinding,
  SecurityNote,
  SecurityScope,
  SecurityWorkspace,
  StaticReviewFinding
} from "../types/api";
import { cn, titleCase } from "../utils";

export function CybersecurityPage() {
  const [dashboard, setDashboard] = useState<SecurityDashboard | null>(null);
  const [workspaces, setWorkspaces] = useState<SecurityWorkspace[]>([]);
  const [scopes, setScopes] = useState<SecurityScope[]>([]);
  const [findings, setFindings] = useState<SecurityFinding[]>([]);
  const [notes, setNotes] = useState<SecurityNote[]>([]);
  const [reviewFindings, setReviewFindings] = useState<StaticReviewFinding[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState("Local Security Lab");
  const [reviewPath, setReviewPath] = useState("backend");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedWorkspace = useMemo(
    () => {
      const fallback = workspaces.length > 0 ? workspaces[0] : null;
      return workspaces.find((workspace) => workspace.id === selectedWorkspaceId) ?? fallback;
    },
    [selectedWorkspaceId, workspaces]
  );

  const load = useCallback(async () => {
    const [nextDashboard, nextWorkspaces, nextScopes, nextFindings, nextNotes] =
      await Promise.all([
        securityApi.dashboard(),
        securityApi.workspaces(),
        securityApi.scopes(selectedWorkspaceId),
        securityApi.findings(),
        securityApi.notes(selectedWorkspaceId)
      ]);
    setDashboard(nextDashboard);
    setWorkspaces(nextWorkspaces.items);
    setScopes(nextScopes.items);
    setFindings(nextFindings.items);
    setNotes(nextNotes.items);
    if (!selectedWorkspaceId && nextWorkspaces.items[0]) {
      setSelectedWorkspaceId(nextWorkspaces.items[0].id);
    }
  }, [selectedWorkspaceId]);

  useEffect(() => {
    void load().catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Security workspace could not be loaded.");
    });
  }, [load]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Security operation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
            Authorized ethical hacking cockpit
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            Ethical Hacking Workspace
          </h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Organize active lab scope, target evidence, findings, notes, and read-only review
            without letting model output authorize execution or expand scope.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            aria-label="Workspace name"
            className="h-9 rounded-lg border border-border-subtle bg-elevated/70 px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={workspaceName}
            onChange={(event) => setWorkspaceName(event.target.value)}
          />
          <Button
            disabled={busy || !workspaceName.trim()}
            icon={<ShieldCheck size={16} />}
            variant="primary"
            onClick={() =>
              void run(async () => {
                const created = await securityApi.createWorkspace({
                  name: workspaceName.trim(),
                  mode: "ethical-hacking",
                  description: "Authorized local ethical hacking workspace."
                });
                setSelectedWorkspaceId(created.id);
              })
            }
          >
            Create
          </Button>
        </div>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="Workspaces" value={dashboard?.workspace_count.toString() ?? "0"} />
        <Metric label="Scopes" value={dashboard?.scope_count.toString() ?? "0"} />
        <Metric label="Findings" value={dashboard?.finding_count.toString() ?? "0"} />
        <Metric label="Modes" value={dashboard?.modes.length.toString() ?? "0"} />
      </section>

      <section className="grid min-h-[62vh] gap-4 xl:grid-cols-[0.9fr_1.15fr_1fr]">
        <Card className="p-0">
          <div className="border-b border-border-subtle p-4">
            <h2 className="flex items-center gap-2 font-semibold">
              <Radar size={17} className="text-accent" />
              Workspaces
            </h2>
          </div>
          <div className="max-h-[62vh] space-y-2 overflow-auto p-3">
            {workspaces.map((workspace) => (
              <button
                key={workspace.id}
                className={cn(
                  "w-full rounded-xl border p-3 text-left transition hover:bg-elevated/70",
                  selectedWorkspace?.id === workspace.id
                    ? "border-accent/40 bg-accent/10"
                    : "border-border-subtle bg-elevated/35"
                )}
                onClick={() => setSelectedWorkspaceId(workspace.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold">{workspace.name}</div>
                    <div className="mt-1 text-xs text-muted">{titleCase(workspace.mode)}</div>
                  </div>
                  <Badge tone={workspace.enabled ? "positive" : "neutral"}>
                    {workspace.enabled ? "Enabled" : "Off"}
                  </Badge>
                </div>
                <p className="mt-3 line-clamp-3 text-xs leading-5 text-muted">
                  {workspace.description || "No description."}
                </p>
              </button>
            ))}
            {workspaces.length === 0 ? (
              <EmptyState title="No ethical hacking workspace yet" icon={<ShieldCheck size={26} />}>
                Create a workspace before recording findings or attaching scope.
              </EmptyState>
            ) : null}
          </div>
        </Card>

        <Card className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="flex items-center gap-2 font-semibold">
                <Crosshair size={17} className="text-accent" />
                Active Scope and Findings
              </h2>
              <p className="mt-1 text-sm text-muted">
                Scopes come from explicit user and policy configuration, never from retrieved text.
              </p>
            </div>
            <Badge tone="accent">{selectedWorkspace?.name ?? "No workspace"}</Badge>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {scopes.map((scope) => (
              <div key={scope.id} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="truncate text-sm font-semibold">{scope.name}</div>
                  <Badge tone={scope.enabled ? "positive" : "neutral"}>{titleCase(scope.scope_type)}</Badge>
                </div>
                <div className="mt-2 break-all font-mono text-xs text-muted">{scope.target}</div>
              </div>
            ))}
            {scopes.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-subtle p-4 text-sm text-muted md:col-span-2">
                No scopes are attached to this workspace.
              </div>
            ) : null}
          </div>
          <div className="space-y-3">
            {findings.slice(0, 5).map((finding) => (
              <FindingRow key={finding.id} finding={finding} />
            ))}
            {findings.length === 0 ? (
              <EmptyState title="No findings recorded" icon={<AlertTriangle size={26} />}>
                Manual findings and persisted static-review observations will appear here.
              </EmptyState>
            ) : null}
          </div>
        </Card>

        <Card className="space-y-4">
          <div>
            <h2 className="flex items-center gap-2 font-semibold">
              <FileSearch size={17} className="text-accent" />
                Evidence Review
            </h2>
            <p className="mt-1 text-sm text-muted">
              Read-only checks inspect repository text for common weakness patterns.
            </p>
          </div>
          <div className="flex gap-2">
            <input
              aria-label="Static review path"
              className="h-10 min-w-0 flex-1 rounded-xl border border-border-subtle bg-elevated/60 px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent"
              value={reviewPath}
              onChange={(event) => setReviewPath(event.target.value)}
            />
            <Button
              disabled={busy || !reviewPath.trim()}
              icon={<Activity size={16} />}
              onClick={() =>
                void run(async () => {
                  const response = await securityApi.staticReview({
                    paths: [reviewPath.trim()],
                    workspace_id: selectedWorkspace?.id ?? null,
                    persist_findings: false
                  });
                  setReviewFindings(response.findings);
                })
              }
            >
              Review
            </Button>
          </div>
          <div className="space-y-2">
            {reviewFindings.map((finding, index) => (
              <div key={`${finding.affected_asset}-${index.toString()}`} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="text-sm font-semibold">{finding.title}</div>
                  <Badge tone={severityTone(finding.severity)}>{titleCase(finding.severity)}</Badge>
                </div>
                <div className="mt-2 break-words text-xs text-muted">{finding.affected_asset}</div>
                <pre className="mt-2 max-h-24 overflow-auto rounded-lg bg-background/70 p-2 text-xs leading-5 text-secondary">
                  {finding.evidence}
                </pre>
              </div>
            ))}
            {reviewFindings.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-subtle p-4 text-sm text-muted">
                Static review results will appear here.
              </div>
            ) : null}
          </div>
          <div className="rounded-xl border border-border-subtle bg-elevated/35 p-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <NotebookPen size={15} className="text-accent" />
              Notes
            </h3>
            <div className="mt-3 space-y-2">
              {notes.slice(0, 3).map((note) => (
                <div key={note.id} className="rounded-lg bg-background/50 p-2">
                  <div className="truncate text-sm font-medium">{note.title}</div>
                  <p className="mt-1 line-clamp-2 text-xs text-muted">{note.content}</p>
                </div>
              ))}
              {notes.length === 0 ? <div className="text-xs text-muted">No notes yet.</div> : null}
            </div>
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

function FindingRow({ finding }: { finding: SecurityFinding }) {
  return (
    <article className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{finding.title}</div>
          <div className="mt-1 truncate text-xs text-muted">
            {finding.affected_asset ?? finding.category ?? "Unassigned"}
          </div>
        </div>
        <Badge tone={severityTone(finding.severity)}>{titleCase(finding.severity)}</Badge>
      </div>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-secondary">
        {finding.description || finding.evidence || "No detail recorded."}
      </p>
    </article>
  );
}

function severityTone(severity: string): "neutral" | "positive" | "warning" | "danger" | "accent" {
  if (severity === "critical" || severity === "high") {
    return "danger";
  }
  if (severity === "medium") {
    return "warning";
  }
  if (severity === "low") {
    return "accent";
  }
  return "neutral";
}
