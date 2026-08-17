import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../../utils";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  icon: ReactNode;
};

export function IconButton({ label, icon, className = "", ...props }: IconButtonProps) {
  return (
    <button
      aria-label={label}
      title={label}
      className={cn(
        "motion-standard inline-flex size-9 items-center justify-center rounded-lg border border-transparent text-muted",
        "transition-[background,border-color,color,opacity,transform] hover:border-border-subtle hover:bg-elevated/80 hover:text-text active:scale-95",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
        className
      )}
      {...props}
    >
      {icon}
    </button>
  );
}
