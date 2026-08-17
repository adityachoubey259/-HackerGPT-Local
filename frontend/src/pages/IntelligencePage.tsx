import { BrainCircuit, Gauge, Route, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { intelligenceApi } from "../api/intelligence";
import { systemApi } from "../api/system";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { useAsyncResource } from "../hooks/useAsyncResource";
import type { ModelCapabilityProfile, RoutingDecision } from "../types/api";
import { titleCase } from "../utils";

export function IntelligencePage() {
  const [message, setMessage] = useState("Implement a secure FastAPI endpoint with tests");
  const [mode, setMode] = useState("auto");
  const [decision, setDecision] = useState<RoutingDecision | null>(null);
  const [profiles, setProfiles] = useState<ModelCapabilityProfile[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const config = useAsyncResource(useCallback((signal) => systemApi.publicConfig(signal), []));

  useEffect(() => {
    void intelligenceApi.profiles().then(setProfiles).catch(() => setProfiles([]));
  }, []);

  async function routeModel() {
    setBusy(true);
    setError(null);
    try {
      setDecision(await intelligenceApi.route({ message, mode }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Routing failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="max-w-3xl">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
          Intelligence engine
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Model Router</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Inspect provider-independent routing decisions without exposing private reasoning or
          silently falling back to cloud endpoints.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <Route size={17} className="text-accent" />
            Routing Request
          </h2>
          <div className="flex flex-wrap gap-2">
            <Badge tone="accent">
              {config.data?.response.default_mode === "direct_expert"
                ? "Direct Expert"
                : "Standard"}
            </Badge>
            <Badge>{config.data ? config.data.response.technical_depth : "unknown"} depth</Badge>
          </div>
          <textarea
            aria-label="Routing message"
            className="min-h-32 rounded-xl border border-border-subtle bg-elevated/60 px-3 py-2 text-sm leading-6 outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            {["auto", "local_only", "quality_first", "speed_first", "low_memory"].map((item) => (
              <button
                key={item}
                className={`rounded-lg border px-3 py-2 text-sm transition ${
                  mode === item
                    ? "border-accent/50 bg-accent/10 text-accent"
                    : "border-border-subtle bg-elevated/50 text-muted hover:text-text"
                }`}
                onClick={() => setMode(item)}
              >
                {titleCase(item)}
              </button>
            ))}
          </div>
          <Button disabled={busy || !message.trim()} icon={<Gauge size={16} />} onClick={() => void routeModel()}>
            Inspect Route
          </Button>
        </Card>

        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <BrainCircuit size={17} className="text-accent" />
            Decision
          </h2>
          {decision ? (
            <div className="space-y-3">
              <div className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={decision.error ? "warning" : "positive"}>
                    {decision.error ? "Diagnostic" : "Selected"}
                  </Badge>
                  <span className="font-mono text-sm">
                    {decision.provider ?? "none"} / {decision.model ?? "none"}
                  </span>
                </div>
                <div className="mt-3 grid gap-2 text-sm text-muted sm:grid-cols-3">
                  <span>Task: {titleCase(decision.task)}</span>
                  <span>Mode: {titleCase(decision.mode)}</span>
                  <span>{decision.manual ? "Manual" : "Automatic"}</span>
                </div>
              </div>
              {decision.error ? (
                <div className="rounded-xl border border-warning/30 bg-warning/10 p-3 text-sm text-warning">
                  {decision.error}
                </div>
              ) : null}
              <div className="space-y-2">
                {decision.candidates.map((candidate) => (
                  <div key={`${candidate.provider}-${candidate.model}`} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold">{candidate.display_name}</div>
                        <div className="mt-1 font-mono text-xs text-muted">
                          {candidate.provider}/{candidate.model}
                        </div>
                      </div>
                      <Badge tone={candidate.local ? "positive" : "warning"}>
                        {candidate.hardware_fit}
                      </Badge>
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs text-muted">
                      {candidate.reasons.join("; ")}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <EmptyState title="No routing decision yet" icon={<Route size={26} />}>
              Submit a task to inspect how the local-first router scores available models.
            </EmptyState>
          )}
        </Card>
      </section>

      <Card className="space-y-3">
        <h2 className="flex items-center gap-2 font-semibold">
          <ShieldCheck size={17} className="text-accent" />
          Model Profiles
        </h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {profiles.map((profile) => (
            <div key={profile.pattern} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
              <div className="font-mono text-sm font-semibold">{profile.pattern}</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {profile.strengths.slice(0, 5).map((strength) => (
                  <Badge key={strength}>{strength}</Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
