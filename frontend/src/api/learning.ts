import { apiClient } from "./client";
import type {
  ArtifactCreate,
  ArtifactEvaluationComparison,
  ArtifactEvaluationRequest,
  DatasetVersion,
  DatasetVersionCreate,
  DatasetBlueprint,
  LearningExample,
  LearningExampleCreate,
  LearningOverview,
  ModelArtifact,
  SeedDatasetImportResult,
  TrainingBackendCapabilities,
  TrainingDatasetExport,
  TrainingJob,
  TrainingJobCreate,
  TrainingPreflightRequest,
  TrainingPreflightResult
} from "../types/api";

export const learningApi = {
  overview: (signal?: AbortSignal) =>
    apiClient.get<LearningOverview>("/api/v1/learning/overview", { signal }),
  examples: (signal?: AbortSignal) =>
    apiClient.get<LearningExample[]>("/api/v1/learning/examples", { signal }),
  directExpertBlueprint: (signal?: AbortSignal) =>
    apiClient.get<DatasetBlueprint>("/api/v1/learning/blueprints/direct-expert", { signal }),
  importDirectExpertBlueprint: (signal?: AbortSignal) =>
    apiClient.post<SeedDatasetImportResult>(
      "/api/v1/learning/blueprints/direct-expert/import",
      {},
      { signal }
    ),
  createExample: (request: LearningExampleCreate, signal?: AbortSignal) =>
    apiClient.post<LearningExample>("/api/v1/learning/examples", request, { signal }),
  datasets: (signal?: AbortSignal) =>
    apiClient.get<DatasetVersion[]>("/api/v1/learning/datasets", { signal }),
  createDataset: (request: DatasetVersionCreate, signal?: AbortSignal) =>
    apiClient.post<DatasetVersion>("/api/v1/learning/datasets", request, { signal }),
  trainingJobs: (signal?: AbortSignal) =>
    apiClient.get<TrainingJob[]>("/api/v1/learning/training/jobs", { signal }),
  trainingBackends: (signal?: AbortSignal) =>
    apiClient.get<TrainingBackendCapabilities[]>("/api/v1/learning/training/backends", {
      signal
    }),
  preflightTraining: (request: TrainingPreflightRequest, signal?: AbortSignal) =>
    apiClient.post<TrainingPreflightResult>("/api/v1/learning/training/preflight", request, {
      signal
    }),
  exportTrainingDataset: (datasetVersionId: string, sequenceLength: number, signal?: AbortSignal) =>
    apiClient.get<TrainingDatasetExport>(
      `/api/v1/learning/training/datasets/${datasetVersionId}/export?sequence_length=${sequenceLength.toString()}`,
      { signal }
    ),
  trainingJob: (jobId: string, signal?: AbortSignal) =>
    apiClient.get<TrainingJob>(`/api/v1/learning/training/jobs/${jobId}`, { signal }),
  createTrainingJob: (request: TrainingJobCreate, signal?: AbortSignal) =>
    apiClient.post<TrainingJob>("/api/v1/learning/training/jobs", request, {
      signal,
      timeoutMs: 60000
    }),
  cancelTrainingJob: (jobId: string, signal?: AbortSignal) =>
    apiClient.post<TrainingJob>(`/api/v1/learning/training/jobs/${jobId}/cancel`, {}, { signal }),
  resumeTrainingJob: (jobId: string, signal?: AbortSignal) =>
    apiClient.post<TrainingJob>(`/api/v1/learning/training/jobs/${jobId}/resume`, {}, { signal }),
  artifacts: (signal?: AbortSignal) =>
    apiClient.get<ModelArtifact[]>("/api/v1/learning/models", { signal }),
  artifact: (artifactId: string, signal?: AbortSignal) =>
    apiClient.get<ModelArtifact>(`/api/v1/learning/models/${artifactId}`, { signal }),
  createArtifact: (request: ArtifactCreate, signal?: AbortSignal) =>
    apiClient.post<ModelArtifact>("/api/v1/learning/models", request, { signal }),
  promoteArtifact: (artifactId: string, signal?: AbortSignal) =>
    apiClient.post<ModelArtifact>(`/api/v1/learning/models/${artifactId}/promote`, {}, { signal }),
  evaluateArtifact: (
    artifactId: string,
    request: ArtifactEvaluationRequest,
    signal?: AbortSignal
  ) =>
    apiClient.post<ArtifactEvaluationComparison>(
      `/api/v1/learning/models/${artifactId}/evaluate`,
      request,
      { signal }
    ),
  rejectArtifact: (artifactId: string, signal?: AbortSignal) =>
    apiClient.post<ModelArtifact>(`/api/v1/learning/models/${artifactId}/reject`, {}, { signal }),
  deleteArtifact: (artifactId: string, signal?: AbortSignal) =>
    apiClient.delete<ModelArtifact>(`/api/v1/learning/models/${artifactId}`, { signal }),
  rollbackArtifact: (signal?: AbortSignal) =>
    apiClient.post<ModelArtifact | null>("/api/v1/learning/models/rollback", {}, { signal })
};
