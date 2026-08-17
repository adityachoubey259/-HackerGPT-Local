import { forwardRef } from "react";
import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

import { cn } from "../../utils";

const controlClass =
  "rounded-lg border border-border-subtle bg-surface/80 text-sm text-text shadow-inner shadow-black/0 transition-[border-color,background,box-shadow] placeholder:text-muted hover:border-border focus:border-focus focus:bg-panel focus:outline-none focus:ring-4 focus:ring-focus/10 disabled:cursor-not-allowed disabled:opacity-55";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className = "", ...props },
  ref
) {
  return (
    <input
      className={cn("h-9 px-3", controlClass, className)}
      ref={ref}
      {...props}
    />
  );
});

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className = "", ...props }, ref) {
  return (
    <textarea
      className={cn("min-h-24 px-3 py-2 leading-6", controlClass, className)}
      ref={ref}
      {...props}
    />
  );
});

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = "", ...props }, ref) {
  return (
    <select
      className={cn("h-9 px-3", controlClass, className)}
      ref={ref}
      {...props}
    />
  );
  }
);
