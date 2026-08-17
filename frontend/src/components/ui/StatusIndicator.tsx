import { Badge } from "./Badge";
import type { ProviderStatus } from "../../types/api";

const tones: Record<ProviderStatus, "neutral" | "positive" | "warning" | "danger" | "accent"> = {
  configured: "accent",
  disabled: "neutral",
  healthy: "positive",
  unavailable: "danger",
  degraded: "warning",
  misconfigured: "danger"
};

export function StatusIndicator({ status }: { status: ProviderStatus }) {
  const tone = tones[status];
  return <Badge tone={tone}>{status}</Badge>;
}
