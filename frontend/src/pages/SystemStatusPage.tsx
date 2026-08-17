import { Activity, Cpu, Database, Gauge, HardDrive, MemoryStick, Server, Zap } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback } from "react";

import { modelsApi } from "../api/models";
import { systemApi } from "../api/system";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { StatusIndicator } from "../components/ui/StatusIndicator";
import { useAsyncResource } from "../hooks/useAsyncResource";
import type { HardwareReport, KnowledgeMemoryStatus, ProviderHealth, SystemInfo } from "../types/api";
import { cn, formatBytes, formatPercent } from "../utils";

export function SystemStatusPage() {
  const system = useAsyncResource<SystemStatusData>(
    useCallback(
      async (signal) => {
        const [info, hardware, knowledgeMemoryStatus, providers] = await Promise.all([
          systemApi.info(signal),
          systemApi.hardware(signal),
          systemApi.knowledgeMemory(signal),
          modelsApi.providers(signal)
        ]);
        return { info, hardware, knowledgeMemory: knowledgeMemoryStatus, providers };
      },
      []
    )
  );

  if (system.loading) {
    return (
      <div className="space-y-4 p-6">
        <SkeletonBar />
        <div className="grid gap-4 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }
  if (system.error || !system.data) {
    return (
      <div className="p-6">
        <EmptyState title="Backend unavailable" icon={<Server size={28} />}>
          {system.error?.message ?? "System status could not be loaded."}
        </EmptyState>
      </div>
    );
  }

  const { info, hardware, knowledgeMemory, providers } = system.data;
  const ramUsedPercent =
    hardware.memory.total_bytes && hardware.memory.available_bytes != null
      ? ((hardware.memory.total_bytes - hardware.memory.available_bytes) / hardware.memory.total_bytes) * 100
      : null;
  const primaryDisk = hardware.disks.length > 0 ? hardware.disks[0] : null;
  const diskUsedPercent =
    primaryDisk?.total_bytes && primaryDisk.free_bytes != null
      ? ((primaryDisk.total_bytes - primaryDisk.free_bytes) / primaryDisk.total_bytes) * 100
      : null;

  return (
    <div className="space-y-5 p-6">
      <header className="max-w-3xl">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
          Developer control center
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">System Status</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Real backend, hardware, provider, and storage diagnostics. This page does not synthesize
          live telemetry that the backend has not reported.
        </p>
      </header>

      <section className="grid gap-3 md:grid-cols-4">
        <MetricTile icon={<Server size={16} />} label="Backend" value="Reachable" tone="positive" />
        <MetricTile icon={<Database size={16} />} label="Database" value={info.database_type} />
        <MetricTile icon={<Cpu size={16} />} label="CPU threads" value={hardware.cpu.logical_processors?.toString() ?? "Unknown"} />
        <MetricTile icon={<Zap size={16} />} label="CUDA" value={hardware.acceleration.cuda_available ? "Available" : "Unavailable"} tone={hardware.acceleration.cuda_available ? "positive" : "warning"} />
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <MetricTile
          icon={<Database size={16} />}
          label="Knowledge docs"
          value={knowledgeMemory.rag.document_count.toString()}
        />
        <MetricTile
          icon={<Database size={16} />}
          label="Knowledge chunks"
          value={knowledgeMemory.rag.chunk_count.toString()}
        />
        <MetricTile
          icon={<MemoryStick size={16} />}
          label="Memories"
          value={knowledgeMemory.memory.memory_count.toString()}
        />
        <MetricTile
          icon={<Gauge size={16} />}
          label="Vector store"
          value={knowledgeMemory.rag.vector_store_status}
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1fr_1fr_0.8fr]">
        <Card>
          <SectionTitle icon={<Activity size={17} />} title="Application" />
          <dl className="mt-4 space-y-2">
            <Info label="Version" value={info.application_version} />
            <Info label="Environment" value={info.environment} />
            <Info label="Python" value={info.python_version} />
            <Info label="OS" value={`${hardware.operating_system} ${hardware.os_release ?? ""}`} />
            <Info label="Architecture" value={hardware.architecture} />
          </dl>
        </Card>

        <Card>
          <SectionTitle icon={<MemoryStick size={17} />} title="Memory And Disk" />
          <div className="mt-4 space-y-5">
            <Meter
              label="RAM used"
              detail={`${formatBytes(hardware.memory.available_bytes)} available of ${formatBytes(hardware.memory.total_bytes)}`}
              percent={ramUsedPercent}
            />
            <Meter
              label="Disk used"
              detail={
                primaryDisk
                  ? `${formatBytes(primaryDisk.free_bytes)} free on ${primaryDisk.path}`
                  : "Disk details unavailable"
              }
              percent={diskUsedPercent}
            />
          </div>
        </Card>

        <Card>
          <SectionTitle icon={<Gauge size={17} />} title="Acceleration" />
          <dl className="mt-4 space-y-2">
            <Info label="CUDA driver" value={hardware.acceleration.cuda_driver_version ?? "Unknown"} />
            <Info
              label="CUDA toolkit"
              value={hardware.acceleration.cuda_toolkit_available ? "Available" : "Unavailable"}
            />
            <Info label="ROCm" value={hardware.acceleration.rocm_available ? "Available" : "Unavailable"} />
            <Info
              label="Apple Metal"
              value={hardware.acceleration.apple_metal_supported ? "Available" : "Unavailable"}
            />
          </dl>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-0">
          <div className="border-b border-border-subtle px-4 py-3">
            <SectionTitle icon={<HardDrive size={17} />} title="GPU" />
          </div>
          <div className="space-y-3 p-4">
            {hardware.gpus.length ? (
              hardware.gpus.map((gpu) => {
                const vramUsedPercent =
                  gpu.vram_total_bytes && gpu.vram_free_bytes != null
                    ? ((gpu.vram_total_bytes - gpu.vram_free_bytes) / gpu.vram_total_bytes) * 100
                    : null;
                return (
                  <div
                    key={`${gpu.name ?? "gpu"}-${gpu.driver_version ?? "driver"}`}
                    className="rounded-xl border border-border-subtle bg-elevated/60 p-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <h3 className="font-medium">{gpu.name ?? "Unknown GPU"}</h3>
                        <p className="mt-1 text-xs text-muted">{gpu.vendor ?? "Unknown vendor"}</p>
                      </div>
                      <span className="text-technical text-xs text-muted">
                        {gpu.compute_capability ?? "Compute unknown"}
                      </span>
                    </div>
                    <div className="mt-4">
                      <Meter
                        label="VRAM used"
                        detail={`${formatBytes(gpu.vram_free_bytes)} free of ${formatBytes(gpu.vram_total_bytes)}`}
                        percent={vramUsedPercent}
                      />
                    </div>
                    <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                      <Info label="Driver" value={gpu.driver_version ?? "Unknown"} />
                      <Info label="CUDA driver" value={gpu.cuda_driver_version ?? "Unknown"} />
                    </dl>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-muted">No GPU information available.</p>
            )}
          </div>
        </Card>

        <Card className="p-0">
          <div className="border-b border-border-subtle px-4 py-3">
            <SectionTitle icon={<Server size={17} />} title="Model Infrastructure" />
          </div>
          <div className="space-y-2 p-4">
            {providers.map((provider) => (
              <ProviderRow key={provider.provider} provider={provider} />
            ))}
            {providers.length === 0 ? (
              <p className="text-sm text-muted">No model providers are configured.</p>
            ) : null}
          </div>
        </Card>
      </section>
    </div>
  );
}

interface SystemStatusData {
  info: SystemInfo;
  hardware: HardwareReport;
  knowledgeMemory: KnowledgeMemoryStatus;
  providers: ProviderHealth[];
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <h2 className="flex items-center gap-2 font-semibold">
      <span className="text-accent">{icon}</span>
      {title}
    </h2>
  );
}

function MetricTile({
  icon,
  label,
  value,
  tone = "accent"
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone?: "accent" | "positive" | "warning";
}) {
  const toneClass = {
    accent: "text-accent",
    positive: "text-positive",
    warning: "text-warning"
  }[tone];
  return (
    <div className="hairline-panel rounded-xl p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-muted">{label}</span>
        <span className={cn("rounded-lg border border-border-subtle bg-elevated p-2", toneClass)}>
          {icon}
        </span>
      </div>
      <div className="mt-3 truncate text-xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}

function Meter({
  label,
  detail,
  percent
}: {
  label: string;
  detail: string;
  percent: number | null;
}) {
  const width = percent == null ? 0 : Math.max(0, Math.min(100, percent));
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-technical text-xs text-muted">{formatPercent(percent)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-elevated">
        <div
          className="h-full rounded-full bg-accent transition-[width]"
          style={{ width: `${width.toString()}%` }}
        />
      </div>
      <div className="mt-1.5 text-xs text-muted">{detail}</div>
    </div>
  );
}

function ProviderRow({ provider }: { provider: ProviderHealth }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border-subtle bg-elevated/60 p-3 text-sm">
      <div className="min-w-0">
        <div className="truncate font-medium">{provider.provider}</div>
        <div className="truncate text-xs text-muted">{provider.base_url ?? "No endpoint"}</div>
      </div>
      <StatusIndicator status={provider.status} />
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="min-w-0 break-words text-right text-secondary">{value || "Unknown"}</dd>
    </div>
  );
}

function SkeletonBar() {
  return <div className="h-24 animate-pulse rounded-xl bg-elevated/60" />;
}

function SkeletonCard() {
  return <div className="h-44 animate-pulse rounded-xl border border-border-subtle bg-elevated/60" />;
}
