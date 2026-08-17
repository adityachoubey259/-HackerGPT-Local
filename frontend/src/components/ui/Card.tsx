import type { HTMLAttributes } from "react";

import { cn } from "../../utils";

export function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("premium-panel rounded-xl p-4", className)}
      {...props}
    />
  );
}
