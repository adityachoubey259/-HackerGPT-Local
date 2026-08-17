import { apiClient } from "./client";
import type {
  SecurityDashboard,
  SecurityFinding,
  SecurityFindingListResponse,
  SecurityNote,
  SecurityNoteListResponse,
  SecurityScope,
  SecurityScopeListResponse,
  SecurityWorkspace,
  SecurityWorkspaceListResponse,
  StaticReviewResponse
} from "../types/api";

export const securityApi = {
  dashboard: () => apiClient.get<SecurityDashboard>("/api/v1/security/dashboard"),
  workspaces: () => apiClient.get<SecurityWorkspaceListResponse>("/api/v1/security/workspaces"),
  createWorkspace: (body: { name: string; mode: string; description: string }) =>
    apiClient.post<SecurityWorkspace>("/api/v1/security/workspaces", body),
  scopes: (workspaceId?: string | null) => {
    const suffix = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
    return apiClient.get<SecurityScopeListResponse>(`/api/v1/security/scopes${suffix}`);
  },
  createScope: (body: {
    name: string;
    scope_type: string;
    target: string;
    workspace_id?: string | null;
    description?: string;
  }) => apiClient.post<SecurityScope>("/api/v1/security/scopes", body),
  findings: () => apiClient.get<SecurityFindingListResponse>("/api/v1/security/findings"),
  createFinding: (body: {
    title: string;
    severity: string;
    confidence: string;
    description: string;
    evidence: string;
    remediation: string;
    workspace_id?: string | null;
  }) => apiClient.post<SecurityFinding>("/api/v1/security/findings", body),
  notes: (workspaceId?: string | null) => {
    const suffix = workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "";
    return apiClient.get<SecurityNoteListResponse>(`/api/v1/security/notes${suffix}`);
  },
  createNote: (body: { title: string; content: string; workspace_id?: string | null }) =>
    apiClient.post<SecurityNote>("/api/v1/security/notes", body),
  staticReview: (body: { paths: string[]; workspace_id?: string | null; persist_findings: boolean }) =>
    apiClient.post<StaticReviewResponse>("/api/v1/security/static-review", body)
};

