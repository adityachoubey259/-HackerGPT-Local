import type { ReactNode } from "react";

import { cn } from "../../utils";

export function EmptyState({
  title,
  children,
  icon,
  className = ""
}: {
  title: string;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex min-h-44 flex-col items-center justify-center rounded-xl border border-dashed border-border-subtle",
        "bg-[linear-gradient(135deg,rgb(var(--color-elevated)/0.9),rgb(var(--color-panel)/0.65))] p-6 text-center",
        className
      )}
    >
      {icon ? (
        <div className="mb-3 rounded-xl border border-accent/20 bg-accent/10 p-3 text-accent shadow-soft">
          {icon}
        </div>
      ) : null}
      <h2 className="text-base font-semibold text-text">{title}</h2>
      <div className="mt-2 max-w-lg text-sm leading-6 text-muted">{children}</div>
    </div>
  );
}
