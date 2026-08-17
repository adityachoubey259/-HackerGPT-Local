import { Clipboard, WandSparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { promptsApi } from "../api/prompts";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import type { PromptArchitectResponse, PromptProfile } from "../types/api";
import { titleCase } from "../utils";

const promptTypes = [
  "coding",
  "frontend",
  "backend",
  "api",
  "sdk",
  "database",
  "ethical_hacking_lab",
  "cybersecurity_lab",
  "research",
  "code_review",
  "migration"
];

export function PromptLabPage() {
  const [profiles, setProfiles] = useState<PromptProfile[]>([]);
  const [objective, setObjective] = useState("Build a production-ready React settings page");
  const [promptType, setPromptType] = useState("frontend");
  const [level, setLevel] = useState("advanced");
  const [language, setLanguage] = useState("TypeScript");
  const [result, setResult] = useState<PromptArchitectResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void promptsApi.profiles().then(setProfiles).catch(() => setProfiles([]));
  }, []);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      setResult(
        await promptsApi.generate({
          objective,
          prompt_type: promptType,
          level,
          language,
          use_live_research:
            promptType === "research" ||
            promptType === "ethical_hacking_lab" ||
            promptType === "cybersecurity_lab",
          constraints: ["Preserve local-first privacy", "Include verification steps"]
        })
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Prompt generation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="max-w-3xl">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
          Prompt architect
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Prompt Lab</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Generate domain-specific prompts that combine agent, model, context, testing, security,
          and live-intelligence constraints without generic filler.
        </p>
      </header>

      {error ? (
        <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.2fr]">
        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <WandSparkles size={17} className="text-accent" />
            Architect Request
          </h2>
          <textarea
            aria-label="Prompt objective"
            className="min-h-36 rounded-xl border border-border-subtle bg-elevated/60 px-3 py-2 text-sm leading-6 outline-none focus-visible:ring-2 focus-visible:ring-accent"
            value={objective}
            onChange={(event) => setObjective(event.target.value)}
          />
          <div className="grid gap-3 sm:grid-cols-3">
            <Select label="Type" value={promptType} values={promptTypes} onChange={setPromptType} />
            <Select
              label="Level"
              value={level}
              values={["quick", "professional", "advanced", "expert", "principal_research"]}
              onChange={setLevel}
            />
            <label className="text-sm">
              <span className="text-muted">Language</span>
              <input
                className="mt-1 h-10 w-full rounded-xl border border-border-subtle bg-elevated/60 px-3 outline-none focus-visible:ring-2 focus-visible:ring-accent"
                value={language}
                onChange={(event) => setLanguage(event.target.value)}
              />
            </label>
          </div>
          <Button
            disabled={busy || !objective.trim()}
            icon={<WandSparkles size={16} />}
            variant="primary"
            onClick={() => void generate()}
          >
            Generate Prompt
          </Button>
        </Card>

        <Card className="space-y-4">
          <h2 className="flex items-center gap-2 font-semibold">
            <Clipboard size={17} className="text-accent" />
            Output
          </h2>
          {result ? (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {result.recommended_agent ? <Badge tone="accent">{result.recommended_agent}</Badge> : null}
                {result.recommended_model_capability ? (
                  <Badge>{result.recommended_model_capability}</Badge>
                ) : null}
                {result.recommended_context_sources.map((source) => (
                  <Badge key={source}>{source}</Badge>
                ))}
              </div>
              <pre className="max-h-[52vh] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-border-subtle bg-background/70 p-4 text-sm leading-6 text-secondary">
                {result.optimized_prompt}
              </pre>
              <div className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
                <div className="text-sm font-semibold">Assumptions</div>
                <ul className="mt-2 space-y-1 text-sm text-muted">
                  {result.assumptions.map((assumption) => (
                    <li key={assumption}>{assumption}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <EmptyState title="No prompt generated" icon={<WandSparkles size={26} />}>
              Create a prompt profile for coding, backend, API, SDK, database, or ethical hacking work.
            </EmptyState>
          )}
        </Card>
      </section>

      <Card className="space-y-3">
        <h2 className="font-semibold">Profiles</h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {profiles.map((profile) => (
            <div key={profile.id} className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
              <div className="text-sm font-semibold">{profile.label}</div>
              <div className="mt-1 text-xs text-muted">{promptTypeLabel(profile.prompt_type)}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function Select({
  label,
  value,
  values,
  onChange
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm">
      <span className="text-muted">{label}</span>
      <select
        className="mt-1 h-10 w-full rounded-xl border border-border-subtle bg-elevated/60 px-3 outline-none focus-visible:ring-2 focus-visible:ring-accent"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {values.map((item) => (
          <option key={item} value={item}>
            {promptTypeLabel(item)}
          </option>
        ))}
      </select>
    </label>
  );
}

function promptTypeLabel(value: string) {
  if (value === "cybersecurity_lab" || value === "ethical_hacking_lab") {
    return "Ethical Hacking Lab";
  }
  return titleCase(value);
}
