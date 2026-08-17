import {
  Bot,
  Brain,
  Database,
  Moon,
  Route,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sun,
  Wrench,
  X
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { IconButton } from "../ui/IconButton";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import { useAgentStore } from "../../stores/agentStore";
import { useModelStore } from "../../stores/modelStore";
import { usePreferenceStore } from "../../stores/preferenceStore";
import { useThemeStore } from "../../stores/themeStore";
import { useUiStore } from "../../stores/uiStore";
import { cn } from "../../utils";

const navigationCommands = [
  { label: "Open Chat", description: "Return to the private intelligence workspace", href: "/", icon: Search },
  { label: "Open Models", description: "Inspect local runtimes and installed models", href: "/models", icon: Bot },
  { label: "Open Knowledge", description: "Manage local RAG sources and citations", href: "/knowledge", icon: Database },
  { label: "Open Ethical Hacking", description: "Scopes, findings, notes, and lab workflows", href: "/ethical-hacking", icon: ShieldCheck },
  { label: "Open Research", description: "Policy-controlled live intelligence", href: "/research", icon: Search },
  { label: "Open Prompt Lab", description: "Generate production-ready expert prompts", href: "/prompts", icon: SlidersHorizontal },
  { label: "Open Learning Studio", description: "Curate examples, datasets, training, and artifacts", href: "/learning", icon: Brain },
  { label: "Open Agents", description: "Inspect and select configured specialists", href: "/agents", icon: Brain },
  { label: "Open Memory", description: "Review explicit local memory", href: "/memory", icon: Database },
  { label: "Open Tools", description: "Audited tool registry and confirmations", href: "/tools", icon: Wrench },
  { label: "Open Intelligence", description: "Model routing and capability diagnostics", href: "/intelligence", icon: Route },
  { label: "Open Settings", description: "Local account and response preferences", href: "/settings", icon: Settings },
  { label: "Open System Status", description: "Hardware and backend diagnostics", href: "/system", icon: SlidersHorizontal }
] as const;

export function CommandPalette() {
  const navigate = useNavigate();
  const open = useUiStore((state) => state.commandPaletteOpen);
  const close = useUiStore((state) => state.closeCommandPalette);
  const toggle = useUiStore((state) => state.toggleCommandPalette);
  const preference = useThemeStore((state) => state.preference);
  const setPreference = useThemeStore((state) => state.setPreference);
  const responsePreferences = usePreferenceStore((state) => state.preferences);
  const loadResponsePreferences = usePreferenceStore((state) => state.load);
  const saveResponsePreferences = usePreferenceStore((state) => state.save);
  const agents = useAgentStore((state) => state.agents);
  const selectAgent = useAgentStore((state) => state.selectAgent);
  const models = useModelStore((state) => state.models);
  const selectModel = useModelStore((state) => state.selectModel);
  const [query, setQuery] = useState("");
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useFocusTrap(dialogRef, open, close);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        toggle();
      }
      if (event.key === "Escape") {
        close();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [close, toggle]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    void loadResponsePreferences();
  }, [loadResponsePreferences, open]);

  const commands = useMemo(() => {
    const themeCommand =
      preference === "dark"
        ? {
            label: "Switch to Light Mode",
            description: "Use the polished light interface",
            icon: Sun,
            action: () => setPreference("light")
          }
        : {
            label: "Switch to Dark Mode",
            description: "Use the flagship dark interface",
            icon: Moon,
            action: () => setPreference("dark")
          };

    return [
      ...navigationCommands.map((command) => ({
        ...command,
        action: () => navigate(command.href)
      })),
      ...models.map((model) => ({
        label: `Use Model: ${model.name}`,
        description: `${model.provider} / ${model.provider_model_id}`,
        icon: Bot,
        action: () => selectModel(model.provider, model.provider_model_id)
      })),
      ...agents
        .filter((agent) => agent.enabled)
        .map((agent) => ({
          label: `Use Agent: ${agent.name}`,
          description: agent.description,
          icon: Brain,
          action: () => selectAgent(agent.id)
        })),
      {
        label:
          responsePreferences?.response_mode === "direct_expert"
            ? "Use Standard Response Mode"
            : "Use Direct Expert Mode",
        description: "Switch persisted response style without changing security policy",
        icon: Brain,
        action: () =>
          void saveResponsePreferences({
            response_mode:
              responsePreferences?.response_mode === "direct_expert" ? "standard" : "direct_expert"
          })
      },
      ...(["auto", "fast", "deep"] as const).map((reasoningMode) => ({
        label: `Reasoning: ${titleCase(reasoningMode)}`,
        description:
          reasoningMode === "fast"
            ? "Prefer visible low-latency answers; disables provider thinking where supported"
            : reasoningMode === "deep"
              ? "Request deeper provider reasoning only when safely configured"
              : "Let routing choose the appropriate reasoning behavior",
        icon: Brain,
        action: () => void saveResponsePreferences({ reasoning_mode: reasoningMode })
      })),
      themeCommand
    ].filter((command) => {
      const searchable = `${command.label} ${command.description}`.toLowerCase();
      return searchable.includes(query.toLowerCase().trim());
    });
  }, [
    agents,
    models,
    navigate,
    preference,
    query,
    responsePreferences?.response_mode,
    saveResponsePreferences,
    selectAgent,
    selectModel,
    setPreference
  ]);

  if (!open) {
    return null;
  }

  return (
    <div
      aria-label="Command palette"
      aria-modal="true"
      className="fixed inset-0 z-modal flex items-start justify-center bg-background/55 px-4 pt-[12vh] backdrop-blur-sm"
      role="dialog"
    >
      <div
        className="w-full max-w-2xl overflow-hidden rounded-2xl border border-border-subtle bg-floating shadow-popover"
        ref={dialogRef}
      >
        <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-3">
          <Search aria-hidden size={18} className="text-muted" />
          <input
            aria-label="Command search"
            autoFocus
            className="h-10 min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-muted"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search commands, pages, and local controls"
            value={query}
          />
          <IconButton label="Close command palette" icon={<X size={16} />} onClick={close} />
        </div>
        <div className="max-h-[420px] overflow-auto p-2">
          {commands.length ? (
            commands.map((command) => {
              const Icon = command.icon;
              return (
                <button
                  className={cn(
                    "motion-standard flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left",
                    "transition-[background,transform] hover:bg-elevated/80 active:translate-y-px"
                  )}
                  key={command.label}
                  onClick={() => {
                    command.action();
                    close();
                  }}
                >
                  <span className="flex size-9 items-center justify-center rounded-lg border border-border-subtle bg-elevated text-accent">
                    <Icon aria-hidden size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-text">{command.label}</span>
                    <span className="block truncate text-xs text-muted">{command.description}</span>
                  </span>
                </button>
              );
            })
          ) : (
            <div className="px-4 py-10 text-center text-sm text-muted">No matching commands.</div>
          )}
        </div>
        <div className="flex items-center justify-between border-t border-border-subtle px-4 py-2 text-xs text-muted">
          <span>Navigation and safe preferences only. Tool execution is never launched here.</span>
          <kbd className="rounded border border-border-subtle bg-elevated px-1.5 py-0.5">Esc</kbd>
        </div>
      </div>
    </div>
  );
}

function titleCase(value: string): string {
  return `${value.slice(0, 1).toUpperCase()}${value.slice(1)}`;
}
