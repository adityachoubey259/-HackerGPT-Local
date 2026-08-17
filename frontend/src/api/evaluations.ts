import { apiClient } from "./client";
import type { EvaluationDataset, EvaluationRun, EvaluationRunRequest } from "../types/api";

export const evaluationsApi = {
  datasets: (signal?: AbortSignal) =>
    apiClient.get<EvaluationDataset[]>("/api/v1/evaluations/datasets", { signal }),
  runs: (signal?: AbortSignal) =>
    apiClient.get<EvaluationRun[]>("/api/v1/evaluations/runs", { signal }),
  run: (request: EvaluationRunRequest, signal?: AbortSignal) =>
    apiClient.post<EvaluationRun>("/api/v1/evaluations/run", request, {
      signal,
      timeoutMs: 60000
    })
};
