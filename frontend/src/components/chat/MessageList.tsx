import { Bot, Cpu, LockKeyhole, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

import { EmptyState } from "../ui/EmptyState";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../../types/api";

const suggestions = [
  "Explain a stack trace",
  "Plan a refactor",
  "Draft a local prompt",
  "Check model runtime"
];

export function MessageList({ messages }: { messages: Message[] }) {
  if (messages.length === 0) {
    return (
      <EmptyState
        className="min-h-[54vh]"
        title="Private AI workstation ready"
        icon={<Bot size={28} />}
      >
        <div className="space-y-5">
          <p>
            Start a private streamed conversation with your selected local runtime. Messages and
            generation telemetry are persisted locally.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            <StatusPill icon={<LockKeyhole size={14} />} label="Local-first boundary" />
            <StatusPill icon={<Cpu size={14} />} label="Runtime-aware shell" />
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {suggestions.map((suggestion) => (
              <span
                className="rounded-full border border-border-subtle bg-panel/70 px-3 py-1 text-xs text-secondary"
                key={suggestion}
              >
                {suggestion}
              </span>
            ))}
          </div>
        </div>
      </EmptyState>
    );
  }
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-2 py-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}

function StatusPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center justify-center gap-2 rounded-lg border border-border-subtle bg-elevated/70 px-3 py-2 text-xs font-medium text-secondary">
      <span className="text-accent">{icon}</span>
      {label}
      <Sparkles aria-hidden size={12} className="text-muted" />
    </span>
  );
}
