import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "../../utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: ReactNode;
};

const variants: Record<ButtonVariant, string> = {
  primary:
    "border border-accent/60 bg-accent text-white shadow-[0_10px_28px_rgb(var(--color-accent)/0.22)] hover:bg-accent-hover dark:text-background",
  secondary:
    "border border-border-subtle bg-elevated/80 text-text hover:border-border hover:bg-panel",
  ghost:
    "border border-transparent text-muted hover:border-border-subtle hover:bg-elevated/70 hover:text-text",
  danger: "border border-danger/60 bg-danger text-white hover:brightness-95"
};

export function Button({
  className = "",
  variant = "secondary",
  icon,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "motion-standard inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3 text-sm font-medium",
        "transition-[background,border-color,box-shadow,color,opacity,transform] active:translate-y-px",
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:active:translate-y-0",
        variants[variant],
        className
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
