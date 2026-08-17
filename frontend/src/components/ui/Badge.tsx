import type { HTMLAttributes } from "react";

import { cn } from "../../utils";

type BadgeTone = "neutral" | "positive" | "warning" | "danger" | "accent";

const tones: Record<BadgeTone, string> = {
  neutral: "border-border-subtle bg-elevated/60 text-muted",
  positive: "border-positive/30 bg-positive/10 text-positive",
  warning: "border-warning/30 bg-warning/10 text-warning",
  danger: "border-danger/30 bg-danger/10 text-danger",
  accent: "border-accent/30 bg-accent/10 text-accent"
};

export function Badge({
  tone = "neutral",
  className = "",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return (
    <span
      className={cn(
        "inline-flex min-h-6 items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
