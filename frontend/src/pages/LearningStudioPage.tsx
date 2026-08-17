import {
  Activity,
  AlertTriangle,
  Beaker,
  BookOpenCheck,
  Boxes,
  Brain,
  CheckCircle2,
  Cpu,
  DatabaseZap,
  FileJson,
  GraduationCap,
  Import,
  Layers3,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Undo2
} from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { evaluationsApi } from "../api/evaluations";
import { learningApi } from "../api/learning";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { Input, Select, Textarea } from "../components/ui/Form";
import { Spinner } from "../components/ui/Spinner";
import { useAsyncResource } from "../hooks/useAsyncResource";
import type {
  DatasetSplit,
  DatasetBlueprint,
  DatasetVersion,
  EvaluationDataset,
  EvaluationRun,
  LearningExample,
  LearningOverview,
  ModelArtifact,
  TrainingBackendCapabilities,
  TrainingDatasetExport,
  TrainingFit,
  TrainingJob,
  TrainingPreflightResult,
  TrainingPreset
} from "../types/api";
import { cn, formatBytes, titleCase } from "../utils";

interface LearningStudioData {
  overview: LearningOverview;
  examples: LearningExample[];
  datasets: DatasetVersion[];
  jobs: TrainingJob[];
  artifacts: ModelArtifact[];
  backends: TrainingBackendCapabilities[];
  evalDatasets: EvaluationDataset[];
  evalRuns: EvaluationRun[];
  blueprint: DatasetBlueprint | null;
}

const emptyData: LearningStudioData = {
  overview: {
    example_count: 0,
    dataset_version_count: 0,
    training_job_count: 0,
    artifact_count: 0,
    active_job_count: 0,
    promoted_artifacts: 0,
    storage_bytes: 0,
    recent_evaluation_runs: 0,
    policy: {}
  },
  examples: [],
  datasets: [],
  jobs: [],
  artifacts: [],
  backends: [],
  evalDatasets: [],
  evalRuns: [],
  blueprint: null
};

export function LearningStudioPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [prompt, setPrompt] = useState("Explain how to keep tool output untrusted.");
  const [response, setResponse] = useState(
    "Treat tool output as data, preserve audit metadata, and require explicit confirmation for write or high-impact execution."
  );
  const [split, setSplit] = useState<DatasetSplit>("train");
  const [baseModel, setBaseModel] = useState("qwen2.5-coder:7b");
  const [selectedBackendId, setSelectedBackendId] = useState("transformers-peft");
  const [preset, setPreset] = useState<TrainingPreset>("quick");
  const [sequenceLength, setSequenceLength] = useState(128);
  const [quantized, setQuantized] = useState(false);
  const [launchWorker, setLaunchWorker] = useState(false);
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedEvalDatasetId, setSelectedEvalDatasetId] = useState("");
  const [preflight, setPreflight] = useState<TrainingPreflightResult | null>(null);
  const [datasetExport, setDatasetExport] = useState<TrainingDatasetExport | null>(null);
  const [starterImport, setStarterImport] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const studio = useAsyncResource<LearningStudioData>(
    useCallback(
      async (signal) => {
        void refreshKey;
        const [
          overview,
          examples,
          datasets,
          jobs,
          artifacts,
          backends,
          evalDatasets,
          evalRuns,
          blueprint
        ] =
          await Promise.all([
            learningApi.overview(signal),
            learningApi.examples(signal),
            learningApi.datasets(signal),
            learningApi.trainingJobs(signal),
            learningApi.artifacts(signal),
            learningApi.trainingBackends(signal),
            evaluationsApi.datasets(signal),
            evaluationsApi.runs(signal),
            learningApi.directExpertBlueprint(signal)
          ]);
        return {
          overview,
          examples,
          datasets,
          jobs,
          artifacts,
          backends,
          evalDatasets,
          evalRuns,
          blueprint
        };
      },
      [refreshKey]
    )
  );

  const data = studio.data ?? emptyData;
  const latestDataset = data.datasets.at(0) ?? null;
  const selectedDataset = useMemo(
    () => data.datasets.find((dataset) => dataset.id === selectedDatasetId) ?? latestDataset,
    [data.datasets, latestDataset, selectedDatasetId]
  );
  const latestEvalDataset = data.evalDatasets.at(0) ?? null;
  const selectedEvalDataset = useMemo(
    () =>
      data.evalDatasets.find((dataset) => dataset.id === selectedEvalDatasetId) ??
      latestEvalDataset,
    [data.evalDatasets, latestEvalDataset, selectedEvalDatasetId]
  );
  const selectedBackend = useMemo(
    () =>
      data.backends.find((backend) => backend.backend_id === selectedBackendId) ??
      data.backends.at(0) ??
      null,
    [data.backends, selectedBackendId]
  );

  useEffect(() => {
    if (!selectedDatasetId && latestDataset) {
      setSelectedDatasetId(latestDataset.id);
    }
  }, [latestDataset, selectedDatasetId]);

  useEffect(() => {
    if (!selectedEvalDatasetId && latestEvalDataset) {
      setSelectedEvalDatasetId(latestEvalDataset.id);
    }
  }, [latestEvalDataset, selectedEvalDatasetId]);

  useEffect(() => {
    if (!data.backends.some((backend) => backend.backend_id === selectedBackendId)) {
      setSelectedBackendId(data.backends.at(0)?.backend_id ?? "transformers-peft");
    }
  }, [data.backends, selectedBackendId]);

  function refresh() {
    setRefreshKey((value) => value + 1);
  }

  async function runAction(name: string, action: () => Promise<void>) {
    setBusyAction(name);
    try {
      await action();
      refresh();
    } finally {
      setBusyAction(null);
    }
  }

  async function addExample() {
    await runAction("example", async () => {
      await learningApi.createExample({
        source_type: "manual",
        prompt,
        response,
        correction: null,
        tags: ["phase-16", "curated", "direct-expert", "ethical-hacking"],
        split,
        provenance: { imported_from: "learning_studio_ui", trusted_instructions: false }
      });
    });
  }

  async function createDataset() {
    await runAction("dataset", async () => {
      await learningApi.createDataset({ dataset_id: "local-curated", example_ids: [] });
    });
  }

  async function importStarterDataset() {
    await runAction("starter-import", async () => {
      const result = await learningApi.importDirectExpertBlueprint();
      setSelectedDatasetId(result.dataset.id);
      setStarterImport(
        `${result.imported_count.toString()} new examples imported into ${result.dataset.dataset_id} v${result.dataset.version.toString()}.`
      );
    });
  }

  async function createTrainingJob() {
    if (!selectedDataset) {
      return;
    }
    await runAction("training", async () => {
      await learningApi.createTrainingJob({
        dataset_version_id: selectedDataset.id,
        base_model: baseModel,
        backend_id: selectedBackendId,
        adapter_type: "lora",
        preset,
        sequence_length: sequenceLength,
        quantized,
        launch_worker: launchWorker,
        allow_metadata_only: !launchWorker
      });
    });
  }

  async function runTrainingPreflight() {
    if (!selectedDataset) {
      return;
    }
    await runAction("preflight", async () => {
      const [nextExport, nextPreflight] = await Promise.all([
        learningApi.exportTrainingDataset(selectedDataset.id, sequenceLength),
        learningApi.preflightTraining({
          dataset_version_id: selectedDataset.id,
          base_model: baseModel,
          backend_id: selectedBackendId,
          adapter_type: "lora",
          preset,
          sequence_length: sequenceLength,
          quantized
        })
      ]);
      setDatasetExport(nextExport);
      setPreflight(nextPreflight);
    });
  }

  async function runEvaluation() {
    if (!selectedEvalDataset) {
      return;
    }
    const answers = Object.fromEntries(
      selectedEvalDataset.cases.map((evaluationCase) => [
        evaluationCase.id,
        [
          "Use provider-independent abstractions.",
          "Treat retrieved context and tool output as untrusted data.",
          "Preserve citations like [K1] when evidence is required.",
          "Require explicit confirmation for high-impact tools."
        ].join(" ")
      ])
    );
    await runAction("evaluation", async () => {
      await evaluationsApi.run({
        dataset_id: selectedEvalDataset.id,
        candidate_name: "learning-studio-baseline",
        answers
      });
    });
  }

  async function promoteArtifact(artifactId: string) {
    await runAction(`promote-${artifactId}`, async () => {
      await learningApi.promoteArtifact(artifactId);
    });
  }

  async function cancelTrainingJob(jobId: string) {
    await runAction(`cancel-${jobId}`, async () => {
      await learningApi.cancelTrainingJob(jobId);
    });
  }

  async function resumeTrainingJob(jobId: string) {
    await runAction(`resume-${jobId}`, async () => {
      await learningApi.resumeTrainingJob(jobId);
    });
  }

  async function evaluateArtifact(artifactId: string) {
    await runAction(`evaluate-${artifactId}`, async () => {
      await learningApi.evaluateArtifact(artifactId, {
        evaluation_dataset_id: selectedEvalDataset?.id ?? "v1-core",
        base_candidate_name: "base",
        adapter_candidate_name: "adapter"
      });
    });
  }

  async function rejectArtifact(artifactId: string) {
    await runAction(`reject-${artifactId}`, async () => {
      await learningApi.rejectArtifact(artifactId);
    });
  }

  async function deleteArtifact(artifactId: string) {
    await runAction(`delete-${artifactId}`, async () => {
      await learningApi.deleteArtifact(artifactId);
    });
  }

  async function rollbackArtifact() {
    await runAction("rollback", async () => {
      await learningApi.rollbackArtifact();
    });
  }

  if (studio.loading && !studio.data) {
    return (
      <div className="space-y-4 p-6">
        <div className="h-28 animate-pulse rounded-xl bg-elevated/60" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="h-52 animate-pulse rounded-xl bg-elevated/60" />
          <div className="h-52 animate-pulse rounded-xl bg-elevated/60" />
          <div className="h-52 animate-pulse rounded-xl bg-elevated/60" />
        </div>
      </div>
    );
  }

  if (studio.error && !studio.data) {
    return (
      <div className="p-6">
        <EmptyState title="Learning Studio unavailable" icon={<GraduationCap size={28} />}>
          {studio.error.message}
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="space-y-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
            Local learning control plane
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Learning Studio</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Curate RAG-ready examples, create auditable dataset versions, run deterministic
            evaluations, and manage optional local training workers without silent self-training or
            automatic model downloads.
          </p>
        </div>
        <Button icon={studio.loading ? <Spinner /> : <RefreshCw size={16} />} onClick={refresh}>
          Refresh
        </Button>
      </header>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric icon={<BookOpenCheck size={16} />} label="Examples" value={data.overview.example_count} />
        <Metric icon={<Layers3 size={16} />} label="Datasets" value={data.overview.dataset_version_count} />
        <Metric icon={<Activity size={16} />} label="Active jobs" value={data.overview.active_job_count} />
        <Metric
          icon={<Sparkles size={16} />}
          label="Promoted artifacts"
          value={data.overview.promoted_artifacts}
        />
      </section>

      <Card className="border-accent/20 bg-accent/5">
        <div className="flex flex-wrap items-start gap-3">
          <div className="rounded-xl border border-accent/20 bg-accent/10 p-2 text-accent">
            <ShieldCheck size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold">Learning boundaries</h2>
            <p className="mt-1 text-sm leading-6 text-muted">
              RAG, memory, prompt/agent learning, and model training remain separate layers. Training
              data is untrusted data; real fine-tuning requires the optional Transformers/PEFT worker,
              local model files, and explicit launch outside the FastAPI request path.
            </p>
          </div>
          <Badge tone="accent">local-first</Badge>
        </div>
      </Card>

      <Card className="operator-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-3xl">
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
              Starter dataset blueprint
            </div>
            <h2 className="mt-2 text-xl font-semibold tracking-tight">
              {data.blueprint?.title ?? "Direct Expert + Ethical Hacking Starter Dataset"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              {data.blueprint?.description ??
                "Import a local starter pack for direct, technical, exact-command-oriented adapter work."}
            </p>
          </div>
          <Button
            icon={busyAction === "starter-import" ? <Spinner /> : <Import size={16} />}
            onClick={() => void importStarterDataset()}
            variant="primary"
          >
            Import Starter Pack
          </Button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[0.75fr_1.25fr]">
          <div className="grid gap-2">
            <Metric
              icon={<FileJson size={16} />}
              label="Seed examples"
              value={data.blueprint?.example_count ?? 0}
            />
            <div className="rounded-xl border border-border-subtle bg-elevated/45 p-3">
              <div className="text-sm font-medium">Tags</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {(data.blueprint?.tags ?? []).slice(0, 10).map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-border-subtle bg-background/45 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium">Example preview</div>
              {starterImport ? <Badge tone="positive">{starterImport}</Badge> : null}
            </div>
            <div className="mt-3 grid gap-2">
              {(data.blueprint?.examples ?? []).slice(0, 3).map((example) => (
                <div
                  className="rounded-lg border border-border-subtle bg-elevated/50 p-3"
                  key={example.user}
                >
                  <div className="line-clamp-1 text-sm font-medium">{example.user}</div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {example.tags.slice(0, 5).map((tag) => (
                      <span
                        className="rounded-full border border-border-subtle px-2 py-0.5 text-technical text-[10px] text-muted"
                        key={tag}
                      >
                        {tag}
                      </span>
                    ))}
                    <span className="rounded-full border border-accent/20 bg-accent/10 px-2 py-0.5 text-technical text-[10px] text-accent">
                      {example.split}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <PanelTitle icon={<DatabaseZap size={17} />} title="Curated Example Intake" />
          <div className="mt-4 grid gap-3">
            <Textarea
              aria-label="Training prompt"
              onChange={(event) => setPrompt(event.target.value)}
              value={prompt}
            />
            <Textarea
              aria-label="Training response"
              onChange={(event) => setResponse(event.target.value)}
              value={response}
            />
            <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
              <Select
                aria-label="Dataset split"
                onChange={(event) => setSplit(event.target.value as DatasetSplit)}
                value={split}
              >
                <option value="train">Train</option>
                <option value="validation">Validation</option>
                <option value="test">Test</option>
              </Select>
              <Button
                icon={busyAction === "example" ? <Spinner /> : <CheckCircle2 size={16} />}
                onClick={() => void addExample()}
                variant="primary"
              >
                Add Example
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-0">
          <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
            <PanelTitle icon={<Boxes size={17} />} title="Dataset Versions" />
            <Button
              icon={busyAction === "dataset" ? <Spinner /> : <Layers3 size={16} />}
              onClick={() => void createDataset()}
            >
              Create Version
            </Button>
          </div>
          <div className="grid gap-3 p-4">
            {data.datasets.map((dataset) => (
              <button
                className={cn(
                  "rounded-xl border p-3 text-left transition hover:border-border hover:bg-elevated/70",
                  dataset.id === selectedDataset?.id
                    ? "border-accent/50 bg-accent/10"
                    : "border-border-subtle bg-surface/70"
                )}
                key={dataset.id}
                onClick={() => setSelectedDatasetId(dataset.id)}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-medium">
                    {dataset.dataset_id} v{dataset.version}
                  </div>
                  <Badge tone={dataset.validation_errors.length ? "warning" : "positive"}>
                    {dataset.validation_errors.length ? "needs validation" : "ready"}
                  </Badge>
                </div>
                <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-3">
                  <span>{dataset.train_count} train</span>
                  <span>{dataset.validation_count} validation</span>
                  <span>{dataset.test_count} test</span>
                </div>
                {dataset.validation_errors.length ? (
                  <p className="mt-2 text-xs text-warning">{dataset.validation_errors.join(" ")}</p>
                ) : null}
              </button>
            ))}
            {data.datasets.length === 0 ? (
              <EmptyState title="No dataset versions" icon={<Boxes size={24} />}>
                Add examples, then create a dataset version for evaluation or adapter metadata.
              </EmptyState>
            ) : null}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <PanelTitle icon={<Brain size={17} />} title="Local Training Worker" />
          <div className="mt-4 grid gap-3">
            <Select
              aria-label="Training backend"
              onChange={(event) => setSelectedBackendId(event.target.value)}
              value={selectedBackend?.backend_id ?? selectedBackendId}
            >
              {data.backends.length ? (
                data.backends.map((backend) => (
                  <option key={backend.backend_id} value={backend.backend_id}>
                    {backend.label}
                  </option>
                ))
              ) : (
                <option value="transformers-peft">Transformers + PEFT LoRA</option>
              )}
            </Select>
            <Input
              aria-label="Base model"
              onChange={(event) => setBaseModel(event.target.value)}
              value={baseModel}
            />
            <div className="grid gap-2 sm:grid-cols-[1fr_0.75fr]">
              <Select
                aria-label="Training preset"
                onChange={(event) => setPreset(event.target.value as TrainingPreset)}
                value={preset}
              >
                <option value="quick">Quick smoke</option>
                <option value="balanced">Balanced LoRA</option>
                <option value="quality">Quality LoRA</option>
              </Select>
              <Input
                aria-label="Sequence length"
                min={32}
                max={8192}
                onChange={(event) => setSequenceLength(Number(event.target.value))}
                type="number"
                value={sequenceLength}
              />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <ToggleRow
                checked={quantized}
                label="Quantized training"
                onChange={setQuantized}
              />
              <ToggleRow
                checked={launchWorker}
                label="Launch worker"
                onChange={setLaunchWorker}
              />
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button
                disabled={!selectedDataset}
                icon={busyAction === "preflight" ? <Spinner /> : <Cpu size={16} />}
                onClick={() => void runTrainingPreflight()}
              >
                Run Preflight
              </Button>
              <Button
                disabled={!selectedDataset}
                icon={busyAction === "training" ? <Spinner /> : <Play size={16} />}
                onClick={() => void createTrainingJob()}
                variant={launchWorker ? "primary" : "secondary"}
              >
                {launchWorker ? "Launch Worker" : "Create Record"}
              </Button>
            </div>
          </div>
          <div className="mt-4 grid gap-3">
            {selectedBackend ? <BackendSummary backend={selectedBackend} /> : null}
            {preflight ? <PreflightSummary preflight={preflight} /> : null}
            {datasetExport ? <DatasetExportSummary datasetExport={datasetExport} /> : null}
          </div>
          <div className="mt-5 space-y-2">
            {data.jobs.slice(0, 5).map((job) => (
              <JobRow
                busyAction={busyAction}
                job={job}
                key={job.id}
                onCancel={cancelTrainingJob}
                onResume={resumeTrainingJob}
              />
            ))}
            {data.jobs.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border-subtle p-4 text-sm text-muted">
                No training jobs have been created.
              </p>
            ) : null}
          </div>
        </Card>

        <Card className="p-0">
          <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
            <PanelTitle icon={<SlidersHorizontal size={17} />} title="Model Registry" />
            <Button icon={<Undo2 size={16} />} onClick={() => void rollbackArtifact()}>
              Roll Back Active
            </Button>
          </div>
          <div className="grid gap-3 p-4">
            {data.artifacts.map((artifact) => (
              <div
                className="rounded-xl border border-border-subtle bg-surface/70 p-3"
                key={artifact.id}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate font-medium">{artifact.name}</h3>
                    <p className="mt-1 truncate text-technical text-xs text-muted">
                      {artifact.base_model} / {artifact.adapter_type}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge tone={artifact.active ? "positive" : "neutral"}>
                      {artifact.active ? "active" : artifact.status}
                    </Badge>
                    <Button
                      className="h-7 px-2 text-xs"
                      icon={busyAction === `evaluate-${artifact.id}` ? <Spinner /> : undefined}
                      onClick={() => void evaluateArtifact(artifact.id)}
                    >
                      Evaluate
                    </Button>
                    <Button
                      className="h-7 px-2 text-xs"
                      disabled={artifact.active}
                      onClick={() => void promoteArtifact(artifact.id)}
                    >
                      Promote
                    </Button>
                    <Button
                      className="h-7 px-2 text-xs"
                      disabled={artifact.active}
                      onClick={() => void rejectArtifact(artifact.id)}
                    >
                      Reject
                    </Button>
                    <Button
                      className="h-7 px-2 text-xs"
                      disabled={artifact.active}
                      icon={busyAction === `delete-${artifact.id}` ? <Spinner /> : <Trash2 size={13} />}
                      onClick={() => void deleteArtifact(artifact.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
                <div className="mt-2 grid gap-1 text-xs text-muted sm:grid-cols-2">
                  <span>{formatBytes(artifact.disk_size_bytes)} tracked on disk</span>
                  <span>{Object.keys(artifact.checksums).length.toString()} checksums</span>
                </div>
              </div>
            ))}
            {data.artifacts.length === 0 ? (
              <EmptyState title="No model artifacts" icon={<GraduationCap size={24} />}>
                Completed metadata-only training jobs create artifact records ready for evaluation.
              </EmptyState>
            ) : null}
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Card>
          <PanelTitle icon={<Beaker size={17} />} title="Evaluation Runner" />
          <div className="mt-4 grid gap-3">
            <Select
              aria-label="Evaluation dataset"
              onChange={(event) => setSelectedEvalDatasetId(event.target.value)}
              value={selectedEvalDataset?.id ?? ""}
            >
              {data.evalDatasets.map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {dataset.id} v{dataset.version}
                </option>
              ))}
            </Select>
            <Button
              disabled={!selectedEvalDataset}
              icon={busyAction === "evaluation" ? <Spinner /> : <Play size={16} />}
              onClick={() => void runEvaluation()}
              variant="primary"
            >
              Run Baseline Eval
            </Button>
          </div>
          {selectedEvalDataset ? (
            <p className="mt-3 text-sm leading-6 text-muted">
              {selectedEvalDataset.cases.length} deterministic cases across{" "}
              {selectedEvalDataset.cases.map((item) => titleCase(item.category)).join(", ")}.
            </p>
          ) : null}
        </Card>

        <Card className="p-0">
          <div className="border-b border-border-subtle px-4 py-3">
            <PanelTitle icon={<Beaker size={17} />} title="Evaluation History" />
          </div>
          <div className="grid gap-3 p-4">
            {data.evalRuns.slice(0, 8).map((run) => (
              <TimelineRow
                badge={`${Math.round(run.summary.mean_score * 100).toString()}%`}
                detail={`${run.summary.passed_cases.toString()} passed of ${run.summary.total_cases.toString()}`}
                key={run.id}
                title={run.candidate_name}
                tone={
                  run.summary.passed_cases === run.summary.total_cases ? "positive" : "warning"
                }
              />
            ))}
            {data.evalRuns.length === 0 ? (
              <EmptyState title="No evaluation runs" icon={<Beaker size={24} />}>
                Run the baseline suite to create a local, file-backed evaluation record.
              </EmptyState>
            ) : null}
          </div>
        </Card>
      </section>
    </div>
  );
}

function ToggleRow({
  checked,
  label,
  onChange
}: {
  checked: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex h-9 cursor-pointer items-center justify-between gap-3 rounded-lg border border-border-subtle bg-surface/70 px-3 text-sm text-muted transition hover:border-border hover:bg-elevated/70">
      <span>{label}</span>
      <input
        checked={checked}
        className="size-4 accent-[rgb(var(--color-accent))]"
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
    </label>
  );
}

function BackendSummary({ backend }: { backend: TrainingBackendCapabilities }) {
  return (
    <div className="rounded-xl border border-border-subtle bg-elevated/55 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Cpu className="text-accent" size={15} />
          {backend.label}
        </div>
        <Badge tone={backend.installed ? "positive" : "warning"}>
          {backend.installed ? "installed" : "optional"}
        </Badge>
      </div>
      <p className="mt-2 text-xs leading-5 text-muted">
        {backend.install_hint ?? "LoRA worker can checkpoint, cancel, and resume supported runs."}
      </p>
    </div>
  );
}

function PreflightSummary({ preflight }: { preflight: TrainingPreflightResult }) {
  return (
    <div className="rounded-xl border border-border-subtle bg-surface/75 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <AlertTriangle className="text-accent" size={15} />
          Hardware preflight
        </div>
        <Badge tone={fitTone(preflight.fit)}>{preflight.fit.replaceAll("_", " ")}</Badge>
      </div>
      <ul className="mt-2 space-y-1 text-xs leading-5 text-muted">
        {preflight.reasons.slice(0, 3).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
        {preflight.warnings.slice(0, 2).map((warning) => (
          <li className="text-warning" key={warning}>
            {warning}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DatasetExportSummary({ datasetExport }: { datasetExport: TrainingDatasetExport }) {
  return (
    <div className="rounded-xl border border-border-subtle bg-surface/75 p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        <FileJson className="text-accent" size={15} />
        Dataset export
      </div>
      <div className="mt-3 grid gap-2 text-xs text-muted sm:grid-cols-3">
        <span>{datasetExport.example_count.toLocaleString()} examples</span>
        <span>{datasetExport.total_estimated_tokens.toLocaleString()} est. tokens</span>
        <span>{datasetExport.duplicate_count.toLocaleString()} duplicates</span>
      </div>
    </div>
  );
}

function JobRow({
  busyAction,
  job,
  onCancel,
  onResume
}: {
  busyAction: string | null;
  job: TrainingJob;
  onCancel: (jobId: string) => Promise<void>;
  onResume: (jobId: string) => Promise<void>;
}) {
  const running = ["queued", "preparing", "loading_model", "running", "training", "saving"].includes(
    job.status
  );
  return (
    <div className="rounded-xl border border-border-subtle bg-elevated/60 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">
            {job.base_model} {job.adapter_type}
          </div>
          <div className="mt-1 line-clamp-2 text-xs leading-5 text-muted">
            {job.logs.at(-1) ?? job.hardware_fit}
          </div>
        </div>
        <Badge tone={job.status === "completed" ? "positive" : running ? "accent" : "warning"}>
          {job.status.replaceAll("_", " ")}
        </Badge>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-border-subtle">
        <div
          className="h-full rounded-full bg-accent transition-[width]"
          style={{ width: `${Math.round(job.progress * 100).toString()}%` }}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span>
          {job.accelerator} / step {job.step.toLocaleString()}
          {job.total_steps ? ` of ${job.total_steps.toLocaleString()}` : ""}
        </span>
        <div className="flex gap-2">
          {running ? (
            <Button
              className="h-7 px-2 text-xs"
              icon={busyAction === `cancel-${job.id}` ? <Spinner /> : undefined}
              onClick={() => void onCancel(job.id)}
            >
              Cancel
            </Button>
          ) : null}
          {job.resumable ? (
            <Button
              className="h-7 px-2 text-xs"
              icon={busyAction === `resume-${job.id}` ? <Spinner /> : <RotateCcw size={13} />}
              onClick={() => void onResume(job.id)}
            >
              Resume
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="hairline-panel rounded-xl p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-muted">{label}</span>
        <span className="rounded-lg border border-border-subtle bg-elevated p-2 text-accent">
          {icon}
        </span>
      </div>
      <div className="mt-3 text-2xl font-semibold tracking-tight">{value.toLocaleString()}</div>
    </div>
  );
}

function fitTone(fit: TrainingFit) {
  if (fit === "recommended" || fit === "possible") {
    return "positive";
  }
  if (fit === "unsupported" || fit === "unlikely_to_fit") {
    return "danger";
  }
  return "warning";
}

function PanelTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <h2 className="flex items-center gap-2 font-semibold">
      <span className="text-accent">{icon}</span>
      {title}
    </h2>
  );
}

function TimelineRow({
  title,
  detail,
  badge,
  tone
}: {
  title: string;
  detail: string;
  badge: string;
  tone: "positive" | "warning";
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-border-subtle bg-elevated/60 p-3">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{title}</div>
        <div className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{detail}</div>
      </div>
      <Badge tone={tone}>{badge}</Badge>
    </div>
  );
}
