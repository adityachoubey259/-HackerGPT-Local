import { Bot, Check, Copy, User } from "lucide-react";
import { useState } from "react";

import { SecureMarkdown } from "../markdown/SecureMarkdown";
import { IconButton } from "../ui/IconButton";
import type { Message } from "../../types/api";
import { cn } from "../../utils";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  return (
    <article className={cn("group flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[78ch] rounded-2xl border px-4 py-3 text-sm leading-6 shadow-sm transition-[border-color,background]",
          isUser
            ? "border-accent/30 bg-accent/10"
            : "border-border-subtle bg-panel/92 hover:border-border"
        )}
      >
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted">
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-lg border",
                isUser
                  ? "border-accent/25 bg-accent/10 text-accent"
                  : "border-border-subtle bg-elevated text-secondary"
              )}
            >
              {isUser ? <User size={13} /> : <Bot size={13} />}
            </span>
            {message.role}
          </div>
          <div className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
            <IconButton
              className="size-7"
              label="Copy message"
              icon={copied ? <Check size={14} /> : <Copy size={14} />}
              onClick={() => {
                void navigator.clipboard.writeText(message.content);
                setCopied(true);
                window.setTimeout(() => setCopied(false), 1200);
              }}
            />
          </div>
        </div>
        <div className="markdown-body">
          <SecureMarkdown content={message.content} />
        </div>
        {message.generation_status && message.generation_status !== "completed" ? (
          <div className="mt-3 rounded-lg border border-border-subtle bg-elevated/70 px-3 py-2 text-xs text-muted">
            Status: {message.generation_status}
            {typeof message.metadata.error_message === "string" ? ` - ${message.metadata.error_message}` : ""}
          </div>
        ) : null}
      </div>
    </article>
  );
}
