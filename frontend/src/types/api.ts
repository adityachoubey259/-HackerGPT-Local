export type ProviderStatus =
  | "configured"
  | "disabled"
  | "healthy"
  | "unavailable"
  | "degraded"
  | "misconfigured";

export type ProviderType = "ollama" | "llama_cpp" | "openai_compatible" | "vllm";

export type ProviderCapability =
  | "chat"
  | "completion"
  | "streaming"
  | "embeddings"
  | "vision"
  | "tool_calling"
  | "model_discovery";

export interface ApiErrorBody {
  code: string;
  message: string;
  request_id: string;
  details: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiErrorBody;
}

export interface AuthUser {
  id: string;
  username: string;
  display_name: string;
  role: string;
  is_bootstrap: boolean;
}

export interface AuthSession {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export type ResponseMode = "standard" | "direct_expert";
export type TechnicalDepth = "standard" | "advanced" | "deep" | "expert";
export type IntelligenceMode = "auto" | "speed" | "quality" | "local_only";
export type ReasoningMode = "auto" | "fast" | "deep";

export interface UserPreferences {
  response_mode: ResponseMode;
  technical_depth: TechnicalDepth;
  default_agent: string | null;
  intelligence_mode: IntelligenceMode;
  reasoning_mode: ReasoningMode;
  theme: "system" | "light" | "dark";
}

export interface UserPreferencesPatch {
  response_mode?: ResponseMode;
  technical_depth?: TechnicalDepth;
  default_agent?: string | null;
  intelligence_mode?: IntelligenceMode;
  reasoning_mode?: ReasoningMode;
  theme?: "system" | "light" | "dark";
}

export interface ProviderHealth {
  provider: string;
  type: ProviderType;
  status: ProviderStatus;
  message: string | null;
  capabilities: ProviderCapability[];
  base_url: string | null;
  details: Record<string, string>;
}

export interface NormalizedModel {
  id: string;
  name: string;
  provider: string;
  provider_model_id: string;
  family: string | null;
  architecture: string | null;
  parameter_count: string | null;
  quantization: string | null;
  context_length: number | null;
  size_bytes: number | null;
  estimated_ram_bytes: number | null;
  estimated_vram_bytes: number | null;
  capabilities: ProviderCapability[];
  modified_at: string | null;
  loaded: boolean | null;
  suitability: string | null;
  metadata: Record<string, unknown>;
}

export interface GenerationSettings {
  temperature: number;
  top_p: number;
  max_output_tokens: number;
  reasoning_mode?: ReasoningMode;
  seed?: number | null;
}

export interface ModelTestRequest {
  provider: string;
  model: string;
  prompt: string;
  settings: GenerationSettings;
}

export interface TokenUsage {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface ModelCallMetrics {
  provider: string;
  model: string;
  duration_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  tokens_per_second: number | null;
  success: boolean;
}

export interface ModelTestResponse {
  provider: string;
  model: string;
  text: string;
  duration_ms: number;
  usage: TokenUsage | null;
  metrics: ModelCallMetrics;
}

export type MessageRole = "user" | "assistant";
export type GenerationStatus =
  | "pending"
  | "streaming"
  | "completed"
  | "cancelled"
  | "failed"
  | "interrupted";

export interface Pagination {
  limit: number;
  offset: number;
  total: number;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  agent_id: string | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  items: Conversation[];
  pagination: Pagination;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  metadata: Record<string, unknown>;
  client_request_id: string | null;
  generation_id: string | null;
  generation_status: GenerationStatus | null;
  provider: string | null;
  model: string | null;
  finish_reason: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  time_to_first_token_ms: number | null;
  duration_ms: number | null;
  tokens_per_second: number | null;
  created_at: string;
  updated_at: string;
}

export interface MessageListResponse {
  items: Message[];
  pagination: Pagination;
}

export interface ChatStreamRequest {
  conversation_id: string | null;
  client_request_id: string;
  message: string;
  provider: string | null;
  model: string | null;
  agent_id: string | null;
  settings: GenerationSettings;
}

export interface StreamMeta {
  request_id: string;
  generation_id: string;
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  provider: string;
  model: string;
  agent_id: string | null;
  created_at: string;
}

export interface StreamMetrics {
  time_to_first_token_ms: number | null;
  duration_ms: number | null;
  tokens_per_second: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
}

export interface StreamContext {
  estimated: boolean;
  context_limit: number;
  reserved_response_tokens: number;
  estimated_prompt_tokens: number;
  response_mode?: string;
  technical_depth?: string;
  messages_included: number;
  messages_omitted: number;
  memory: {
    memory_id: string;
    citation_id: string;
    title: string;
    memory_type: string;
    scope: string;
    relevance: number;
  }[];
  rag: {
    citation_id: string;
    chunk_id: string;
    document_id: string;
    file_name: string;
    source_path: string | null;
    page_number: number | null;
    section: string | null;
    score: number | null;
  }[];
  agent: AgentDefinition | null;
}

export type ContextStrategy =
  | "balanced"
  | "conversation-heavy"
  | "knowledge-heavy"
  | "code-focused"
  | "concise"
  | "diagnostic";

export interface AgentDefinition {
  id: string;
  name: string;
  description: string;
  icon: string;
  system_prompt: string;
  preferred_provider: string | null;
  preferred_model: string | null;
  temperature: number;
  top_p: number;
  max_output_tokens: number;
  allowed_tools: string[];
  memory_config: {
    enabled: boolean;
    memory_types: string[];
    maximum_memories: number;
    project_memory: boolean;
    conversation_summaries: boolean;
  };
  rag_config: {
    enabled: boolean;
    knowledge_scope: string;
    result_limit: number;
    reranking: boolean;
    source_diversity: boolean;
  };
  context_strategy: ContextStrategy;
  required_model_capabilities: string[];
  tool_execution_config: {
    enabled: boolean;
    max_tool_calls: number;
    require_confirmation_for_write: boolean;
    require_confirmation_for_high_impact: boolean;
  };
  enabled: boolean;
  built_in: boolean;
  metadata: Record<string, unknown>;
}

export type PermissionClass = "READ_ONLY" | "WRITE_LOCAL" | "HIGH_IMPACT" | "NETWORK";
export type ToolStatus =
  | "requested"
  | "pending_confirmation"
  | "running"
  | "completed"
  | "failed"
  | "denied"
  | "timed_out"
  | "cancelled";

export interface ToolDefinition {
  name: string;
  description: string;
  permission_class: PermissionClass;
  capabilities: string[];
  input_schema: Record<string, unknown>;
  enabled: boolean;
}

export interface ToolExecution {
  id: string;
  tool_name: string;
  permission_class: PermissionClass;
  status: ToolStatus;
  input: Record<string, unknown>;
  working_directory: string | null;
  command_display: string | null;
  stdout: string | null;
  stderr: string | null;
  exit_code: number | null;
  data: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  truncated: boolean;
  duration_ms: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ToolConfirmation {
  id: string;
  execution_id: string;
  tool_name: string;
  permission_class: PermissionClass;
  status: string;
  risk_summary: string;
  expires_at: string;
  created_at: string;
}

export interface ToolExecuteResponse {
  execution: ToolExecution;
  confirmation: ToolConfirmation | null;
  decision: string;
  reason: string;
}

export interface ToolExecutionListResponse {
  items: ToolExecution[];
  total: number;
}

export interface StreamError {
  code: string;
  message: string;
  request_id: string;
  generation_id: string | null;
  retryable: boolean;
}

export interface StreamDone {
  assistant_message_id: string;
  status: GenerationStatus;
  finish_reason: string | null;
}

export type ChatStreamEvent =
  | { event: "meta"; data: StreamMeta }
  | { event: "delta"; data: { text: string } }
  | { event: "usage"; data: TokenUsage & { estimated: boolean } }
  | { event: "context"; data: StreamContext }
  | { event: "metrics"; data: StreamMetrics }
  | { event: "error"; data: StreamError }
  | { event: "done"; data: StreamDone };

export interface HealthResponse {
  status: string;
}

export interface SystemInfo {
  application_version: string;
  environment: string;
  python_version: string;
  operating_system: string;
  architecture: string;
  hostname: string | null;
  database_type: string;
  debug: boolean;
  uptime_seconds: number;
}

export interface KnowledgeMemoryStatus {
  rag: KnowledgeStats;
  memory: {
    enabled: boolean;
    memory_count: number;
    semantic_store_status: string;
  };
}

export type DocumentStatus = "pending" | "indexing" | "indexed" | "failed" | "unsupported" | "deleted";

export interface KnowledgeDocument {
  id: string;
  name: string;
  source: string;
  source_path: string | null;
  mime_type: string | null;
  size_bytes: number;
  checksum: string;
  status: DocumentStatus;
  parser: string | null;
  title: string | null;
  tags: string[];
  metadata: Record<string, unknown>;
  failure_code: string | null;
  failure_message: string | null;
  indexed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  citation_id: string;
  text: string;
  page_number: number | null;
  section: string | null;
  token_count: number;
  character_count: number;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface IngestionJob {
  id: string;
  document_id: string | null;
  source: string;
  status: "queued" | "running" | "completed" | "failed" | "partial";
  total_files: number;
  processed_files: number;
  chunks_indexed: number;
  failure_code: string | null;
  failure_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeListResponse {
  items: KnowledgeDocument[];
  total: number;
}

export interface KnowledgeDetailResponse {
  document: KnowledgeDocument;
  chunks: KnowledgeChunk[];
}

export interface KnowledgeSearchResult {
  chunk_id: string;
  document_id: string;
  citation_id: string;
  text: string;
  score: number;
  file_name: string;
  source_path: string | null;
  page_number: number | null;
  section: string | null;
  metadata: Record<string, unknown>;
}

export interface KnowledgeSearchResponse {
  items: KnowledgeSearchResult[];
  citations: Record<string, unknown>[];
  diagnostics: Record<string, unknown>;
}

export interface KnowledgeStats {
  document_count: number;
  chunk_count: number;
  embedding_provider: string;
  embedding_model: string;
  vector_store: string;
  vector_store_status: string;
}

export type MemoryType = "user" | "project" | "conversation_summary";
export type MemoryScope = "user" | "project" | "conversation";

export interface MemoryItem {
  id: string;
  memory_type: MemoryType;
  scope: MemoryScope;
  project_id: string | null;
  conversation_id: string | null;
  title: string;
  content: string;
  summary: string | null;
  source: string;
  source_message_id: string | null;
  importance: number;
  pinned: boolean;
  enabled: boolean;
  tags: string[];
  metadata: Record<string, unknown>;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  items: MemoryItem[];
  total: number;
}

export interface MemorySearchResponse {
  items: { memory: MemoryItem; relevance: number }[];
  diagnostics: Record<string, unknown>;
}

export interface MemoryExportResponse {
  exported_at: string;
  items: MemoryItem[];
}

export interface PublicConfig {
  environment: string;
  debug: boolean;
  network_access: boolean;
  api: Record<string, unknown>;
  model_endpoint: Record<string, unknown>;
  response: {
    default_mode: string;
    directness: string;
    technical_depth: string;
    assume_technical_user: boolean;
    generic_disclaimers: boolean;
    moralizing: boolean;
    shallow_keyword_filtering: boolean;
    prefer_complete_code: boolean;
    prefer_exact_commands: boolean;
    verify_current_information: boolean;
    investigate_before_unknown: boolean;
    cite_retrieved_sources: boolean;
  };
}

export interface HardwareReport {
  operating_system: string;
  os_release: string | null;
  architecture: string;
  cpu: {
    model: string | null;
    physical_cores: number | null;
    logical_processors: number | null;
  };
  memory: {
    total_bytes: number | null;
    available_bytes: number | null;
  };
  gpus: {
    name: string | null;
    vendor: string | null;
    vram_total_bytes: number | null;
    vram_free_bytes: number | null;
    driver_version: string | null;
    cuda_driver_version: string | null;
    compute_capability: string | null;
  }[];
  acceleration: {
    cuda_available: boolean;
    cuda_driver_version: string | null;
    cuda_toolkit_available: boolean;
    rocm_available: boolean;
    apple_metal_supported: boolean;
  };
  disks: {
    path: string;
    total_bytes: number | null;
    free_bytes: number | null;
  }[];
  detection_warnings: string[];
}

export interface SecurityWorkspace {
  id: string;
  name: string;
  mode: string;
  description: string;
  active_scope_id: string | null;
  enabled: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SecurityScope {
  id: string;
  workspace_id: string | null;
  name: string;
  scope_type: string;
  target: string;
  description: string;
  enabled: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SecurityFinding {
  id: string;
  workspace_id: string | null;
  scope_id: string | null;
  title: string;
  severity: string;
  confidence: string;
  category: string | null;
  cwe: string | null;
  cve: string | null;
  affected_asset: string | null;
  description: string;
  evidence: string;
  remediation: string;
  references: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SecurityNote {
  id: string;
  workspace_id: string | null;
  finding_id: string | null;
  title: string;
  content: string;
  tags: string[];
  references: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SecurityDashboard {
  modes: string[];
  scope_types: string[];
  severity_levels: string[];
  confidence_levels: string[];
  policy_scopes: Record<string, unknown>[];
  workspace_count: number;
  scope_count: number;
  finding_count: number;
}

export interface SecurityWorkspaceListResponse {
  items: SecurityWorkspace[];
}

export interface SecurityScopeListResponse {
  items: SecurityScope[];
}

export interface SecurityFindingListResponse {
  items: SecurityFinding[];
  total: number;
}

export interface SecurityNoteListResponse {
  items: SecurityNote[];
}

export interface StaticReviewFinding {
  title: string;
  severity: string;
  confidence: string;
  category: string;
  affected_asset: string;
  evidence: string;
  remediation: string;
  cwe: string | null;
}

export interface StaticReviewResponse {
  findings: StaticReviewFinding[];
  persisted: number;
  scanned_files: number;
  skipped_files: number;
  diagnostics: Record<string, unknown>;
}

export interface ResearchStatus {
  enabled: boolean;
  search_enabled: boolean;
  provider: string;
  configured: boolean;
  allowed_domains: string[];
  blocked_domains: string[];
  max_results: number;
  cache_ttl_seconds: number;
  official_sources_preferred: boolean;
  private_networks_blocked: boolean;
}

export interface ResearchSession {
  id: string;
  query: string;
  status: string;
  provider: string | null;
  answer: string;
  official_only: boolean;
  filters: Record<string, unknown>;
  diagnostics: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ResearchSource {
  id: string;
  citation_id: string;
  url: string;
  normalized_url: string;
  domain: string;
  title: string;
  source_type: string;
  reliability: string;
  excerpt: string;
  content_checksum: string | null;
  retrieved_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ResearchRunResponse {
  session: ResearchSession;
  sources: ResearchSource[];
}

export interface ResearchHistoryResponse {
  items: ResearchSession[];
  total: number;
}

export interface ModelCandidate {
  provider: string;
  model: string;
  display_name: string;
  score: number;
  hardware_fit: string;
  local: boolean;
  reasons: string[];
  warnings: string[];
}

export interface RoutingDecision {
  provider: string | null;
  model: string | null;
  mode: string;
  task: string;
  manual: boolean;
  candidates: ModelCandidate[];
  diagnostics: string[];
  error: string | null;
}

export interface ModelCapabilityProfile {
  pattern: string;
  strengths: string[];
  weaknesses: string[];
  context_length: number | null;
  max_output_tokens: number | null;
  coding_score: number;
  reasoning_score: number;
  speed_score: number;
  tool_support: boolean | null;
  vision: boolean | null;
  structured_output: boolean | null;
  recommended_agents: string[];
  estimated_vram_bytes: number | null;
  estimated_ram_bytes: number | null;
  default_generation: Record<string, unknown>;
}

export interface PromptProfile {
  id: string;
  label: string;
  prompt_type: string;
  domains: string[];
  languages: string[];
  default_agent: string | null;
  recommended_capabilities: string[];
  required_context_sources: string[];
  checklist: string[];
}

export interface PromptArchitectResponse {
  optimized_prompt: string;
  system_prompt: string | null;
  structured_output_schema: Record<string, unknown> | null;
  recommended_agent: string | null;
  recommended_model_capability: string | null;
  recommended_context_sources: string[];
  assumptions: string[];
  profile: PromptProfile | null;
}

export type LearningSourceType =
  | "manual"
  | "chat"
  | "correction"
  | "file"
  | "folder"
  | "repository"
  | "research"
  | "api"
  | "database";

export type DatasetSplit = "train" | "validation" | "test";
export type TrainingJobStatus =
  | "queued"
  | "preparing"
  | "loading_model"
  | "running"
  | "training"
  | "validating"
  | "saving"
  | "evaluating"
  | "completed"
  | "cancelled"
  | "failed"
  | "interrupted"
  | "requires_backend";
export type TrainingFit = "recommended" | "possible" | "slow" | "unlikely_to_fit" | "unsupported";
export type TrainingPreset = "quick" | "balanced" | "quality" | "custom";
export type ArtifactStatus =
  | "registered"
  | "draft"
  | "validated"
  | "evaluated"
  | "promoted"
  | "rejected"
  | "archived"
  | "rolled_back"
  | "deleted";

export interface TrainingBackendCapabilities {
  backend_id: string;
  label: string;
  supported_model_families: string[];
  adapter_types: string[];
  quantized_training_available: boolean;
  gpu_required: boolean;
  cpu_compatible: boolean;
  checkpoint_support: boolean;
  resume_support: boolean;
  cancellation_support: boolean;
  installed: boolean;
  install_hint: string | null;
}

export interface TrainingPresetConfig {
  preset: TrainingPreset;
  epochs: number;
  max_steps: number;
  learning_rate: number;
  batch_size: number;
  gradient_accumulation_steps: number;
  sequence_length: number;
  lora_rank: number;
  lora_alpha: number;
  lora_dropout: number;
  validation_split: number;
}

export interface TrainingPreflightRequest {
  dataset_version_id: string;
  base_model: string;
  backend_id: string;
  adapter_type: string;
  preset: TrainingPreset;
  sequence_length: number;
  quantized: boolean;
}

export interface TrainingPreflightResult {
  backend: TrainingBackendCapabilities;
  fit: TrainingFit;
  reasons: string[];
  warnings: string[];
  hardware: Record<string, unknown>;
  dataset: Record<string, unknown>;
  preset: TrainingPresetConfig;
}

export interface TrainingDatasetExport {
  dataset_version_id: string;
  export_path: string;
  example_count: number;
  train_count: number;
  validation_count: number;
  test_count: number;
  duplicate_count: number;
  min_tokens: number;
  max_tokens: number;
  median_tokens: number;
  p95_tokens: number;
  total_estimated_tokens: number;
  validation_errors: string[];
  warnings: string[];
}

export interface ArtifactEvaluationRequest {
  evaluation_dataset_id: string;
  base_candidate_name: string;
  adapter_candidate_name: string;
}

export interface ArtifactEvaluationComparison {
  artifact_id: string;
  evaluation_dataset_id: string;
  base_run_id: string;
  adapter_run_id: string;
  by_category: Record<string, string>;
  promoted_allowed: boolean;
  blocking_regressions: string[];
}

export interface LearningExample {
  id: string;
  source_type: LearningSourceType;
  prompt: string;
  response: string;
  correction: string | null;
  tags: string[];
  split: DatasetSplit;
  provenance: Record<string, unknown>;
  checksum: string;
  created_at: string;
}

export interface LearningExampleCreate {
  source_type: LearningSourceType;
  prompt: string;
  response: string;
  correction?: string | null;
  tags: string[];
  split: DatasetSplit;
  provenance: Record<string, unknown>;
}

export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version: number;
  example_ids: string[];
  train_count: number;
  validation_count: number;
  test_count: number;
  validation_errors: string[];
  checksum: string;
  created_at: string;
}

export interface DatasetVersionCreate {
  dataset_id: string;
  example_ids: string[];
}

export interface TrainingJob {
  id: string;
  dataset_version_id: string;
  base_model: string;
  adapter_type: string;
  status: TrainingJobStatus;
  backend_id: string;
  preset: string;
  progress: number;
  loss: number | null;
  step: number;
  total_steps: number | null;
  epoch: number | null;
  validation_loss: number | null;
  learning_rate: number | null;
  elapsed_seconds: number;
  accelerator: string;
  hardware_fit: string;
  logs: string[];
  artifact_id: string | null;
  checkpoint_path: string | null;
  artifact_path: string | null;
  resumable: boolean;
  pid: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TrainingJobCreate {
  dataset_version_id: string;
  base_model: string;
  backend_id?: string;
  adapter_type: string;
  preset?: TrainingPreset;
  sequence_length?: number;
  quantized?: boolean;
  allow_metadata_only: boolean;
  launch_worker?: boolean;
}

export interface ModelArtifact {
  id: string;
  name: string;
  base_model: string;
  adapter_type: string;
  dataset_version_id: string | null;
  evaluation_run_id: string | null;
  status: ArtifactStatus;
  active: boolean;
  promoted_at: string | null;
  disk_size_bytes: number | null;
  checksums: Record<string, string>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ArtifactCreate {
  name: string;
  base_model: string;
  adapter_type: string;
  dataset_version_id?: string | null;
  evaluation_run_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface LearningOverview {
  example_count: number;
  dataset_version_count: number;
  training_job_count: number;
  artifact_count: number;
  active_job_count: number;
  promoted_artifacts: number;
  storage_bytes: number;
  recent_evaluation_runs: number;
  policy: Record<string, unknown>;
}

export interface DatasetBlueprintExample {
  system: string;
  user: string;
  assistant: string;
  metadata: Record<string, unknown>;
  tags: string[];
  split: DatasetSplit;
}

export interface DatasetBlueprint {
  id: string;
  version: string;
  title: string;
  description: string;
  format: string;
  example_path: string;
  recommended_workflow: string[];
  categories: string[];
  tags: string[];
  security_notes: string[];
  example_count: number;
  examples: DatasetBlueprintExample[];
}

export interface SeedDatasetImportResult {
  blueprint_id: string;
  imported_count: number;
  example_count: number;
  dataset: DatasetVersion;
}

export type EvaluationCategory =
  | "coding"
  | "debugging"
  | "prompt_generation"
  | "rag"
  | "research"
  | "security_lab"
  | "ethical_hacking_lab"
  | "general";
export type EvaluationDifficulty = "easy" | "medium" | "hard";

export interface EvaluationCase {
  id: string;
  category: EvaluationCategory;
  difficulty: EvaluationDifficulty;
  prompt: string;
  expected_characteristics: string[];
  required_citations: string[];
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface EvaluationDataset {
  id: string;
  version: string;
  description: string;
  cases: EvaluationCase[];
  metadata: Record<string, unknown>;
}

export interface EvaluationRunRequest {
  dataset_id: string;
  candidate_name: string;
  answers: Record<string, string>;
  compare_to?: string | null;
}

export interface EvaluationCaseResult {
  case_id: string;
  score: number;
  passed: boolean;
  missing_characteristics: string[];
  citation_failures: string[];
  notes: string[];
}

export interface EvaluationSummary {
  total_cases: number;
  passed_cases: number;
  mean_score: number;
  by_category: Record<string, Record<string, number>>;
}

export interface EvaluationRun {
  id: string;
  dataset_id: string;
  dataset_version: string;
  candidate_name: string;
  results: EvaluationCaseResult[];
  summary: EvaluationSummary;
  created_at: string;
  metadata: Record<string, unknown>;
}
