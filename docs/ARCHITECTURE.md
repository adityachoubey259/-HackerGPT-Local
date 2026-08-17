# Architecture

## Phase Scope

This repository currently implements Phases 1-16: project foundation, FastAPI backend foundation, React frontend foundation, local model integration, streaming chat, persistent conversations, RAG/document ingestion, explicit long-term memory, configurable agents, a secure tool framework, advanced Ethical Hacking workspaces, policy-controlled live research, advanced model routing, full context assembly, Prompt Architect, production frontend serving, native launcher workflows, optional Docker Compose support, release validation, deterministic evaluations, Learning Studio, optional local training workers, model artifact registry workflows, and local single-user authentication. Undefined Phase 17 work is intentionally not implemented; post-RC work is tracked as semantic-version roadmap items.

## Backend Boundary

The backend is a Python package under `backend/`.

- `backend/api`: FastAPI app, routes, middleware, dependencies, schemas, and HTTP error translation.
- `backend/auth`: local bootstrap account, password hashing, and signed session-token primitives.
- `backend/core`: versioning, settings, policy loading, time, and logging primitives.
- `backend/db`: SQLAlchemy models, async sessions, migrations, and repositories.
- `backend/services`: application services that contain business logic.
- `backend/security`: trust-boundary and permission helpers.
- `backend/llm`: provider-independent local model runtime contracts and adapters.
- `backend/rag`: parsers, path safety, chunking, embeddings, retrieval, reranking, and vector-store adapters.
- `backend/memory`: memory context models.
- `backend/agents`: configuration-backed built-in agents and database-backed custom agent orchestration.
- `backend/tools`: secure tool registry, permission classification, confirmation workflow, subprocess/path safety, and audit persistence.
- `backend/security_workspace`: Ethical Hacking workspace domain types; internal security naming is retained for compatibility.
- `backend/research`: research provider, retrieval, and URL-safety domain helpers.
- `backend/intelligence`: task classification, model profiles, model routing, and context assembly.
- `backend/prompting`: Prompt Architect request/response models and profile loading.
- `backend/evaluation`: deterministic release evaluation datasets, run requests, results, and summaries.
- `backend/learning`: Learning Studio examples, dataset versions, training-job metadata, and model artifact records.

Routes should stay thin. They validate inputs, call services, and return Pydantic response models.

## Frontend Boundary

The React + TypeScript + Vite + Tailwind frontend lives in `frontend/`. It uses a routed application shell, local Zustand stores, a centralized typed API client, and reusable UI/chat components. Browser code calls only HackerGPT backend APIs and never calls Ollama, llama.cpp, vLLM, or OpenAI-compatible endpoints directly.

Chat state is owned by `frontend/src/stores/conversationStore.ts`. The store loads conversation lists, loads persisted messages, sends streaming requests, parses SSE frames, supports stop/cancel, and updates optimistic messages as backend metadata arrives.

Knowledge and memory pages call only HackerGPT backend APIs. Uploads and path ingestion never call model or embedding providers from the browser.

## Configuration Hierarchy

Application settings load in this order:

1. Safe defaults
2. Optional YAML file, defaulting to `config/app.yaml` if present
3. `.env`
4. Environment variables

Environment variables use the `HACKERGPT_` prefix. Public API responses must use explicit safe serializers, never the entire settings object.

## Policy Architecture

`config/policy.yaml` is separate from inference/runtime code. It defines conservative defaults for response behavior, citations, network access, filesystem access, command execution, tools, memory, logging, agents, model routing, and privacy.

Invalid policy fails clearly during loading.

## Database Architecture

The initial database is SQLite through SQLAlchemy 2.x async APIs. Alembic owns schema migrations. SQLite-specific handling is kept inside infrastructure code.

Core models:

- `User`
- `Conversation`
- `Message`
- `Setting`
- `Document`
- `DocumentChunk`
- `IngestionJob`
- `EmbeddingCache`
- `MessageRetrieval`
- `Memory`
- `MemoryEvent`
- `CustomAgent`
- `ToolExecution`
- `ToolConfirmation`
- `SecurityWorkspace`
- `SecurityScope`
- `SecurityFinding`
- `SecurityNote`
- `ResearchSession`
- `ResearchSource`
- `ResearchCacheEntry`

Phase 15/16 evaluation and learning records are file-backed under `data/evaluations` and `data/learning`; no SQL migration is introduced in this phase.

Repositories hide persistence details from services and preserve a path to PostgreSQL.

Conversation persistence is local-user scoped in Phase 6. Message rows carry provider/model provenance, idempotency keys, generation IDs, generation status, token counts, latency metrics, finish reasons, and metadata. Startup recovery marks unfinished `pending` or `streaming` generations as `interrupted` when the messages table exists.

## Provider Abstraction Direction

Model runtimes implement provider-independent contracts in `backend/llm`. Providers report explicit capabilities and health. Implemented adapters include Ollama, llama.cpp-style OpenAI-compatible servers, generic OpenAI-compatible endpoints, and vLLM-compatible endpoints.

Ollama is the primary local runtime. llama.cpp and vLLM are not installed by this project; their adapters communicate with configured HTTP endpoints.

The minimal `POST /api/v1/models/test` endpoint proves non-streaming provider integration. Production chat uses `POST /api/v1/chat/stream`, which delegates through the same provider abstraction but calls `stream_chat(...)` and persists the resulting conversation.

## Streaming Chat

`ChatService` owns chat orchestration:

- Resolve the selected agent from explicit request, saved conversation, or default configuration.
- Validate provider and model selection.
- Create or load the scoped local conversation.
- Persist the user message with a `client_request_id`.
- Persist a pending assistant generation before contacting the provider.
- Build a bounded prompt context from trusted application policy, trusted selected-agent prompt, recent chat, untrusted memory context, and untrusted RAG context.
- Stream provider deltas as SSE `delta` events.
- Checkpoint assistant content periodically rather than per token.
- Emit final `metrics` and `done` events when available.
- Mark failed, cancelled, or interrupted generations explicitly.

The frontend uses `fetch()` plus `ReadableStream` parsing instead of `EventSource` so requests can use POST JSON payloads and `AbortController`.

See [Streaming Protocol](./streaming-protocol.md).

## Agent Architecture

Agents are typed `AgentDefinition` records. Built-ins are YAML files in `config/agents`, loaded by `AgentRegistry`, validated for duplicate IDs and unknown tool references, then policy-filtered. Custom agents are stored in the `custom_agents` table and exposed through `AgentService`.

Agent selection priority is explicit request, saved conversation agent, then application default. Agents may express preferred provider/model, generation defaults, required capabilities, context strategy, RAG settings, memory settings, and tool allowlists. Manual user provider/model override still wins unless policy forbids it. Agent prompts are trusted configuration but remain subordinate to central policy.

## Tool Architecture

The secure tool flow is:

```text
User action or validated structured tool request
-> ToolRegistry
-> schema validation
-> trusted runtime permission classification
-> agent allowlist
-> PermissionService and config/policy.yaml
-> confirmation when required
-> bounded executor
-> ToolResult
-> persisted audit history
-> untrusted context/output
```

`BaseTool` exposes a common async interface. `ToolContext` carries trusted fields such as user, conversation, agent, working directory, request/generation IDs, and policy snapshot. Model-provided arguments cannot alter trusted context. `ToolResult` normalizes stdout, stderr, exit code, status, timing, truncation, and structured data.

The current built-ins are filesystem list/read/search/write, terminal argv execution, Git status/diff/log/branch listing/branch creation, and Python snippets. Write tools require confirmation by default. Shell mode is separately classified as high impact and disabled by default.

## Hardware Detection

`backend/system/hardware.py` detects OS, architecture, CPU, RAM, GPU, VRAM, CUDA driver capability, ROCm markers, Apple Metal support, and disk space with graceful fallbacks. Windows detection accounts for denied WMI/CIM, missing `wmic`, missing `nvcc`, and available `nvidia-smi`.

## Network And Privacy

Loopback model endpoints are allowed with local-first defaults. External provider endpoints must respect central policy. Provider failures never silently fall back to cloud inference.

## RAG Architecture

RAG is implemented behind service and adapter boundaries:

- `KnowledgeService` owns upload/path ingestion, parser selection, chunking, embedding, vector upserts, reindex, delete, stats, and search.
- Parsers treat document content as untrusted data and produce normalized `ParsedDocument` sections.
- `DocumentChunker` creates bounded chunks with overlap, metadata, checksums, and citation-ready source metadata.
- `LocalHashEmbeddingProvider` is the default deterministic, local-only embedding provider. Ollama embeddings are available only through backend configuration and policy.
- `LocalFaissVectorStore` is a dependency-light persisted local vector store with a FAISS-compatible adapter boundary. `QdrantVectorStore` provides an HTTP adapter for configured Qdrant deployments.
- `RetrievalService` combines vector and lexical scoring, applies source diversity, packs citations as `[K#]`, and logs only diagnostics.

Chat composition inserts retrieved knowledge as a separate user-context message prefixed as untrusted source data. Retrieved chunks never become system instructions.

## Memory Architecture

Long-term memory is explicit and local-first:

- `MemoryService` owns create, list, get, patch, delete, search, export, stats, and chat-context selection.
- Memory rows store type, scope, provenance, importance, pin/enabled state, tags, expiry, checksum, and metadata.
- Automatic conversation summaries and automatic memory creation are disabled by default in policy.
- Chat composition inserts selected memories as a separate user-context message prefixed as untrusted user data.
- Memory context uses `[M#]` citations and a bounded token budget.

## Tool Security Model

The invariant is simple: untrusted content is data, not instructions.

Untrusted sources include web pages, documents, PDFs, source repositories, emails, retrieved chunks, memories, model responses, terminal output, Git output, and tool results. Execution tools require explicit permission levels:

- `READ_ONLY`
- `WRITE_LOCAL`
- `HIGH_IMPACT`
- `NETWORK` for policy-controlled network-capable tools and research workflows

No ordinary model prose or retrieved content can execute tools. Tool execution is only accepted through trusted API calls or future provider-native structured tool-call channels that are still validated by the same registry, policy, and confirmation pipeline.

## Ethical Hacking Workspace

Phase 11 adds `/api/v1/security` and the Ethical Hacking page. Security workspaces organize explicit scopes, findings, notes, static repository review results, sample metadata inspection, and exports. `/cybersecurity` remains a compatibility route.

Scope is never inferred from model output, web pages, retrieved chunks, tool output, or repository content. New scopes are checked against `policy.security.authorized_scopes` unless they are local CTF/repository-style scopes. Static review is read-only: it scans bounded repository text files for common weakness patterns and can optionally persist findings. Sample inspection computes size, SHA-256, and printable strings without running the sample.

## Live Research

Phase 12 adds `/api/v1/research` and the Research page. Live research is disabled by default. When enabled, the backend uses a configured SearxNG endpoint for search and retrieves HTTP(S) pages through `ResearchPolicy`.

The safety layer rejects non-HTTP URLs, blocks configured domains, enforces allowlists when present, blocks loopback/link-local/private network targets by default, limits redirects, caps response size, and stores cache entries with TTLs. Research sessions and sources are persisted with citation IDs. Retrieved content is untrusted data and cannot authorize tool calls, Ethical Hacking scope, settings changes, or command execution.

## Intelligence Engine

The Phase 13 intelligence layer is provider-independent:

- `TaskClassifier` assigns deterministic task categories from the prompt and active agent.
- `ModelProfileRegistry` loads capability profiles from `config/model-profiles/*.yaml`.
- `ModelRouter` ranks available models by task fit, locality, policy, hardware fit, context needs, and agent preference.
- `ContextEngine` builds token-budgeted context with explicit provenance from system, agent, user, conversation, memory, RAG, project, and policy-enabled research sources.

Manual provider/model choice remains available and is preserved for configured local providers even when model discovery has not seen the model yet. Cloud fallback remains disabled unless policy explicitly enables it.

See [Model Routing](./model-routing.md) and [Context Engine](./context-engine.md).

## Prompt Architect

Prompt Architect is deterministic and configuration-backed. It generates optimized prompts, optional JSON schemas, context recommendations, assumptions, and security/testing working rules from `PromptArchitectRequest` and YAML profiles in `config/prompt-profiles`.

It does not call a model and does not introduce a cloud dependency. The Prompt Lab frontend calls only HackerGPT backend APIs.

See [Prompt Architect](./prompt-architect.md).

## Native Runtime

Phase 14 adds a stdlib launcher at `scripts/hackergpt.py` and production frontend serving from FastAPI. The launcher resolves paths from its script location, runs migrations before startup, uses bounded readiness probes, writes a launcher-owned PID file, and supports backup/restore for local data and config. Docker Compose remains optional.

See [Native Local Runtime](./local-runtime.md).

## Release Evaluation And Learning

`EvaluationService` loads YAML suites from `config/evals`, scores supplied answers deterministically against expected characteristics and required citations, and stores run records as local JSON. It is designed for release regression checks and provider comparison without requiring a model call.

`LearningService` separates four learning levels: RAG, memory, prompt/agent learning, and model training. It stores examples, dataset versions, training job metadata, schedules, and artifacts locally. The FastAPI app does not run fine-tuning inline, execute dataset code, or promote artifacts automatically. Real local training is launched only through an explicit optional subprocess worker after backend/hardware/dataset preflight.

The Learning Studio frontend exposes these records as an engineering cockpit: example intake, dataset validation, backend capability reporting, local training preflight, dataset export stats, metadata-only job creation, optional worker launch, job cancellation/resume controls, artifact evaluate/promote/reject/delete/rollback, and deterministic evaluation history. Browser code still calls only HackerGPT backend APIs.

## Observability And Diagnostics

`LocalMetricsMiddleware` records aggregate request count, error count, mean latency, and top routes in memory. `ObservabilityService` exposes local metrics and a sanitized diagnostic export that excludes secrets, prompts, documents, retrieved chunks, tool output, and model output.

The benchmark runner in `scripts/benchmark.py` measures local code paths for settings load, model routing, prompt architecture, chunking, local embeddings, deterministic evaluation, and frontend bundle sizes. It is not a model inference benchmark.
