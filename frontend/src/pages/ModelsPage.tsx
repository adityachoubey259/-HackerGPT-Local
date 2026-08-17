import { Cpu, Gauge, HardDrive, Layers3, RefreshCw, Send } from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";

import { ApiClientError } from "../api/client";
import { modelsApi } from "../api/models";
import { SecureMarkdown } from "../components/markdown/SecureMarkdown";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input, Select, Textarea } from "../components/ui/Form";
import { Spinner } from "../components/ui/Spinner";
import { StatusIndicator } from "../components/ui/StatusIndicator";
import { useModelStore } from "../stores/modelStore";
import type { ModelTestResponse, NormalizedModel, ProviderHealth } from "../types/api";
import { cn, formatBytes, formatPercent, titleCase } from "../utils";

export function ModelsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiClientError | null>(null);
  const [prompt, setPrompt] = useState("Say hello from the selected local model.");
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(0.9);
  const [maxTokens, setMaxTokens] = useState(96);
  const [testResult, setTestResult] = useState<ModelTestResponse | null>(null);
  const [testError, setTestError] = useState<ApiClientError | null>(null);
  const [runningTest, setRunningTest] = useState(false);
  const providers = useModelStore((state) => state.providers);
  const models = useModelStore((state) => state.models);
  const setProviders = useModelStore((state) => state.setProviders);
  const setModels = useModelStore((state) => state.setModels);
  const selectedProvider = useModelStore((state) => state.selectedProvider);
  const selectedModel = useModelStore((state) => state.selectedModel);
  const selectModel = useModelStore((state) => state.selectModel);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextProviders, nextModels] = await Promise.all([
        modelsApi.providers(),
        modelsApi.models()
      ]);
      setProviders(nextProviders);
      setModels(nextModels);
      if (!selectedProvider && nextModels[0]) {
        selectModel(nextModels[0].provider, nextModels[0].provider_model_id);
      }
    } catch (unknownError) {
      setError(
        unknownError instanceof ApiClientError
          ? unknownError
          : new ApiClientError("Unable to load models.", { code: "CLIENT_ERROR", status: null })
      );
    } finally {
      setLoading(false);
    }
  }, [selectModel, selectedProvider, setModels, setProviders]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const selected = models.find(
    (model) => model.provider === selectedProvider && model.provider_model_id === selectedModel
  );
  const healthyCount = providers.filter((provider) => provider.status === "healthy").length;
  const loadedCount = models.filter((model) => model.loaded).length;

  async function runTest() {
    if (!selectedProvider || !selectedModel || !prompt.trim()) {
      return;
    }
    setRunningTest(true);
    setTestError(null);
    setTestResult(null);
    try {
      setTestResult(
        await modelsApi.test({
          provider: selectedProvider,
          model: selectedModel,
          prompt,
          settings: {
            temperature,
            top_p: topP,
            max_output_tokens: maxTokens
          }
        })
      );
    } catch (unknownError) {
      setTestError(
        unknownError instanceof ApiClientError
          ? unknownError
          : new ApiClientError("Model test failed.", { code: "CLIENT_ERROR", status: null })
      );
    } finally {
      setRunningTest(false);
    }
  }

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
            Local runtime dashboard
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Models</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Provider health, installed model discovery, and non-streaming runtime tests without
            browser-to-model endpoint access.
          </p>
        </div>
        <Button icon={<RefreshCw size={16} />} onClick={() => void refresh()}>
          Refresh
        </Button>
      </header>

      {error ? <ErrorNotice error={error} /> : null}

      <section className="grid gap-3 md:grid-cols-3">
        <RuntimeMetric
          icon={<Gauge size={16} />}
          label="Healthy providers"
          value={`${healthyCount.toString()}/${providers.length.toString()}`}
        />
        <RuntimeMetric icon={<Layers3 size={16} />} label="Installed models" value={models.length.toString()} />
        <RuntimeMetric icon={<Cpu size={16} />} label="Loaded models" value={loadedCount.toString()} />
      </section>

      <section className="grid gap-3 lg:grid-cols-4">
        {providers.map((provider) => (
          <ProviderCard key={provider.provider} provider={provider} />
        ))}
        {!loading && providers.length === 0 ? (
          <Card className="text-sm text-muted">No providers configured.</Card>
        ) : null}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <Card className="p-0">
          <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
            <div>
              <h2 className="font-semibold">Discovered Models</h2>
              <p className="text-xs text-muted">Select the model used by the Phase 4 runtime test.</p>
            </div>
            {loading ? <Spinner /> : null}
          </div>
          <div className="grid gap-3 p-4">
            {models.map((model) => (
              <ModelRow
                key={model.id}
                model={model}
                selected={model.id === selected?.id}
                onSelect={() => selectModel(model.provider, model.provider_model_id)}
              />
            ))}
            {!loading && models.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border-subtle bg-elevated/60 p-6 text-center text-sm text-muted">
                No installed models were discovered from enabled providers.
              </div>
            ) : null}
          </div>
        </Card>

        <Card className="sticky top-6 self-start">
          <h2 className="font-semibold">Model Runtime Test</h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            A backend-mediated non-streaming connectivity check, not the final chat flow.
          </p>
          <div className="mt-4 grid gap-3">
            <Select
              aria-label="Provider"
              value={selectedProvider ?? ""}
              onChange={(event) => selectModel(event.target.value, selectedModel ?? "")}
            >
              <option value="">Select provider</option>
              {providers.map((provider) => (
                <option key={provider.provider} value={provider.provider}>
                  {provider.provider}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Installed model"
              value={selectedModel ?? ""}
              onChange={(event) => {
                if (selectedProvider) {
                  selectModel(selectedProvider, event.target.value);
                }
              }}
            >
              <option value="">Select model</option>
              {models
                .filter((model) => !selectedProvider || model.provider === selectedProvider)
                .map((model) => (
                  <option key={model.id} value={model.provider_model_id}>
                    {model.name}
                  </option>
                ))}
            </Select>
            <Textarea
              aria-label="Test prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <div className="grid grid-cols-3 gap-2">
              <Input
                aria-label="Temperature"
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(event) => setTemperature(Number(event.target.value))}
              />
              <Input
                aria-label="Top P"
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={topP}
                onChange={(event) => setTopP(Number(event.target.value))}
              />
              <Input
                aria-label="Max output tokens"
                type="number"
                min="1"
                max="4096"
                value={maxTokens}
                onChange={(event) => setMaxTokens(Number(event.target.value))}
              />
            </div>
            <Button
              variant="primary"
              icon={runningTest ? <Spinner /> : <Send size={16} />}
              disabled={!selectedProvider || !selectedModel || runningTest}
              onClick={() => void runTest()}
            >
              Run Test
            </Button>
            {testError ? <ErrorNotice error={testError} /> : null}
            {testResult ? (
              <div className="rounded-xl border border-border-subtle bg-elevated/70 p-3 text-sm">
                <div className="mb-2 flex flex-wrap gap-2 text-xs text-muted">
                  <Badge tone="accent">{testResult.duration_ms.toFixed(1)} ms</Badge>
                  {testResult.metrics.tokens_per_second !== null ? (
                    <Badge tone="positive">
                      {testResult.metrics.tokens_per_second.toFixed(1)} tok/s
                    </Badge>
                  ) : null}
                </div>
                <div className="markdown-body">
                  <SecureMarkdown content={testResult.text} />
                </div>
              </div>
            ) : null}
          </div>
        </Card>
      </section>
    </div>
  );
}

function RuntimeMetric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="hairline-panel rounded-xl p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted">{label}</span>
        <span className="rounded-lg border border-border-subtle bg-elevated p-2 text-accent">{icon}</span>
      </div>
      <div className="mt-3 text-2xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}

function ProviderCard({ provider }: { provider: ProviderHealth }) {
  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 className="truncate font-semibold">{provider.provider}</h2>
          <div className="mt-1 text-xs text-muted">{titleCase(provider.type)}</div>
        </div>
        <StatusIndicator status={provider.status} />
      </div>
      <div className="break-all rounded-lg border border-border-subtle bg-elevated/70 px-2 py-1.5 text-technical text-xs text-muted">
        {provider.base_url ?? "No endpoint"}
      </div>
      <p className="min-h-10 text-sm leading-5 text-secondary">
        {provider.message ?? "No status message."}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {provider.capabilities.slice(0, 3).map((capability) => (
          <Badge key={capability}>{capability}</Badge>
        ))}
      </div>
    </Card>
  );
}

function ModelRow({
  model,
  selected,
  onSelect
}: {
  model: NormalizedModel;
  selected: boolean;
  onSelect: () => void;
}) {
  const fitPercent =
    model.estimated_vram_bytes && model.size_bytes
      ? Math.min(100, (model.size_bytes / model.estimated_vram_bytes) * 100)
      : null;

  return (
    <button
      className={cn(
        "motion-standard rounded-xl border p-4 text-left transition-[background,border-color,box-shadow,transform] hover:-translate-y-0.5",
        selected
          ? "border-accent/70 bg-accent/10 shadow-[0_16px_36px_rgb(var(--color-accent)/0.14)]"
          : "border-border-subtle bg-surface/80 hover:border-border hover:bg-elevated/70"
      )}
      onClick={onSelect}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold">{model.name}</div>
          <div className="mt-1 truncate text-technical text-xs text-muted">{model.provider_model_id}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {model.loaded ? <Badge tone="positive">Loaded</Badge> : <Badge>Not loaded</Badge>}
          {model.suitability ? <Badge tone="accent">{model.suitability}</Badge> : null}
        </div>
      </div>
      <dl className="mt-4 grid gap-3 text-xs text-muted sm:grid-cols-3">
        <Metric label="Family" value={model.family} />
        <Metric label="Params" value={model.parameter_count} />
        <Metric label="Quant" value={model.quantization} />
        <Metric label="Context" value={model.context_length?.toLocaleString()} />
        <Metric label="Size" value={formatBytes(model.size_bytes)} />
        <Metric label="VRAM est." value={formatBytes(model.estimated_vram_bytes)} />
      </dl>
      <div className="mt-4">
        <div className="mb-1.5 flex items-center justify-between text-xs text-muted">
          <span className="flex items-center gap-1.5">
            <HardDrive size={13} />
            Fit estimate
          </span>
          <span>{formatPercent(fitPercent)}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-elevated">
          <div
            className="h-full rounded-full bg-accent transition-[width]"
            style={{
              width: fitPercent == null ? "0%" : `${Math.min(100, fitPercent).toString()}%`
            }}
          />
        </div>
      </div>
    </button>
  );
}

function Metric({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className="mt-1 font-medium text-text">{value ?? "Unknown"}</dd>
    </div>
  );
}

function ErrorNotice({ error }: { error: ApiClientError }) {
  return (
    <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
      <div className="font-medium">{error.code}</div>
      <div>{error.message}</div>
      {error.requestId ? <div className="mt-1 text-xs">Request ID: {error.requestId}</div> : null}
    </div>
  );
}
