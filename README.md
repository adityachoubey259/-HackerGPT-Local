# HackerGPT Local

HackerGPT Local is a local-first, privacy-first AI platform foundation. Phases 1-16 establish the backend architecture, React frontend shell, model provider abstraction, Ollama integration, hardware diagnostics, configuration, policy, security, database, migrations, streaming chat, persistent conversations, RAG, document ingestion, explicit long-term memory, configurable agents, a secure tool framework, an authorized Ethical Hacking workspace, policy-controlled live research, model routing, prompt architecture, full context assembly, native local startup, release validation, deterministic evaluations, Learning Studio, optional local training workers, and model artifact registry workflows.

## Current Status

Implemented:

- Python/FastAPI backend foundation
- Typed application configuration with defaults, YAML, `.env`, and environment overrides
- Central `config/policy.yaml` with typed validation
- Structured logging and request correlation IDs
- Async SQLAlchemy SQLite database foundation
- Initial Alembic migration for users, conversations, messages, and settings
- Versioned API routes for health, readiness, system info, and public config
- Repository and service boundaries
- Tests for config, policy, security, database, migrations, and API behavior
- React + TypeScript + Vite + Tailwind frontend foundation
- Main application shell with chat, models, settings, and system status pages
- Secure Markdown rendering with sanitized raw HTML handling
- Provider-independent model runtime layer
- Ollama provider over HTTP
- llama.cpp, vLLM, and OpenAI-compatible endpoint adapters
- Hardware detection with Windows/Linux/macOS fallbacks
- Model discovery, provider status, and non-streaming model runtime test endpoint
- Persistent conversation CRUD with scoped local-user repositories
- Streaming chat orchestration over `POST /api/v1/chat/stream`
- Provider-independent chat streaming contracts for Ollama and OpenAI-compatible runtimes
- Idempotent client request handling, generation cancellation, restart recovery, and persisted token/latency metrics
- Frontend streamed message rendering, conversation sidebar, search, archive, rename, delete, stop generation, and generation inspector telemetry
- Document upload and safe allowed-root path ingestion
- Parsers for text, Markdown, HTML, JSON/JSONL, CSV/TSV, source files, DOCX, and basic PDF extraction
- Chunking, deterministic local embeddings, embedding cache, persisted FAISS-style local vector store, and Qdrant HTTP adapter
- Retrieval with citations, source diversity, context budgets, and chat SSE context telemetry
- Explicit long-term memory CRUD/search/export with local-only storage and policy controls
- Configuration-backed built-in agents plus database-backed custom agents
- Active agent selection integrated into chat context, model preferences, memory, RAG, and tool allowlists
- Secure tool registry with filesystem, terminal argv, Git, and Python tool families
- Central permission service with `READ_ONLY`, `WRITE_LOCAL`, `HIGH_IMPACT`, and future `NETWORK` classes
- Confirmation workflow, execution audit history, bounded output capture, subprocess timeouts, and path allowlists
- Advanced Ethical Hacking workspace APIs and UI for workspaces, authorized scopes, findings, notes, static repository review, sample metadata inspection, and report export
- Policy-controlled live research APIs and UI with SearxNG adapter support, source safety checks, private-network blocking, cache entries, sessions, citations, and explicit offline behavior
- Provider-independent intelligence engine with deterministic task classification, local-first model routing, model capability profiles, hardware-fit scoring, and manual route preservation
- Full context engine that assembles system, agent, user, conversation, memory, RAG, project, and policy-enabled research context with token budgets and provenance diagnostics
- Prompt Architect APIs and Prompt Lab UI for domain-aware prompt generation, structured-output scaffolds, context recommendations, and security/testing working rules
- Local single-user authentication with a backend-seeded bootstrap admin, hashed password storage, signed httpOnly session cookie, authenticated API middleware, route guard, and session restore
- Native stdlib launcher at `scripts/hackergpt.py` for doctor, start, stop, status, backup, and restore workflows
- Production local frontend serving from the FastAPI backend when `frontend/dist` exists
- Optional Docker Compose support for the API plus profiled local Qdrant and research services
- Deterministic release evaluation suites in `config/evals`
- File-backed evaluation run history
- Learning Studio API and UI for example curation, dataset versions, optional real training preflight/worker launch, and model artifact evaluate/promote/reject/delete/rollback
- Direct Expert + Ethical Hacking starter dataset blueprint with importable chat-style JSONL examples for Learning Studio
- Sanitized diagnostics export and local request metrics
- Local benchmark runner and performance baseline documentation
- Native launcher pre-migration backup before startup migrations
- Release candidate metadata for `1.0.0-rc.1`

Deferred to later phases:

- Final `1.0.0` stamp after host visual acceptance, real local provider smoke testing, native launcher acceptance, real local training verification, and distribution acceptance
- v1.1 roadmap items documented in `docs/roadmap-v1.1.md`; no undefined Phase 17 is implemented

## Prerequisites

- Windows x64 or another Python 3.12-compatible development machine
- Python 3.12
- Git
- Optional: Docker and Docker Compose for later containerized workflows

## Setup

PowerShell-friendly commands:

```powershell
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
cd frontend
npm.cmd install
```

Optional real local LoRA training dependencies are separate from the core install:

```powershell
python -m pip install -e ".[training]"
```

The training worker loads model files with local-only settings and does not download model weights
automatically.

Local login defaults to `admin` / `admin987` for first-run single-user use. See
`docs/local-auth.md` for the bootstrap, hashing, and session-cookie behavior.

The Direct Expert starter dataset is documented in `docs/direct-expert-training-blueprint.md`.

`make` shortcuts are provided, but every command also has a direct equivalent for Windows.

## Backend Development

Run the API with the application factory:

```powershell
python -m uvicorn backend.api.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Useful endpoints:

- `POST http://127.0.0.1:8000/api/v1/auth/login`
- `POST http://127.0.0.1:8000/api/v1/auth/change-password`
- `POST http://127.0.0.1:8000/api/v1/auth/logout`
- `GET http://127.0.0.1:8000/api/v1/auth/me`
- `GET http://127.0.0.1:8000/api/v1/preferences`
- `PATCH http://127.0.0.1:8000/api/v1/preferences`
- `GET http://127.0.0.1:8000/api/v1/health`
- `GET http://127.0.0.1:8000/api/v1/health/ready`
- `GET http://127.0.0.1:8000/api/v1/system/info`
- `GET http://127.0.0.1:8000/api/v1/system/hardware`
- `GET http://127.0.0.1:8000/api/v1/config/public`
- `GET http://127.0.0.1:8000/api/v1/models/providers`
- `GET http://127.0.0.1:8000/api/v1/models`
- `GET http://127.0.0.1:8000/api/v1/conversations`
- `POST http://127.0.0.1:8000/api/v1/chat/stream`
- `POST http://127.0.0.1:8000/api/v1/chat/generations/{generation_id}/cancel`
- `GET http://127.0.0.1:8000/api/v1/knowledge`
- `POST http://127.0.0.1:8000/api/v1/knowledge/upload`
- `POST http://127.0.0.1:8000/api/v1/knowledge/ingest-path`
- `POST http://127.0.0.1:8000/api/v1/knowledge/search`
- `GET http://127.0.0.1:8000/api/v1/memory`
- `POST http://127.0.0.1:8000/api/v1/memory`
- `POST http://127.0.0.1:8000/api/v1/memory/search`
- `POST http://127.0.0.1:8000/api/v1/memory/export`
- `GET http://127.0.0.1:8000/api/v1/agents`
- `POST http://127.0.0.1:8000/api/v1/agents`
- `PATCH http://127.0.0.1:8000/api/v1/agents/{agent_id}`
- `DELETE http://127.0.0.1:8000/api/v1/agents/{agent_id}`
- `POST http://127.0.0.1:8000/api/v1/agents/{agent_id}/duplicate`
- `GET http://127.0.0.1:8000/api/v1/tools`
- `POST http://127.0.0.1:8000/api/v1/tools/execute`
- `GET http://127.0.0.1:8000/api/v1/tools/executions`
- `POST http://127.0.0.1:8000/api/v1/tools/executions/{execution_id}/cancel`
- `GET http://127.0.0.1:8000/api/v1/tools/confirmations`
- `POST http://127.0.0.1:8000/api/v1/tools/confirmations/{confirmation_id}/approve`
- `POST http://127.0.0.1:8000/api/v1/tools/confirmations/{confirmation_id}/deny`
- `GET http://127.0.0.1:8000/api/v1/security/dashboard`
- `GET http://127.0.0.1:8000/api/v1/security/workspaces`
- `POST http://127.0.0.1:8000/api/v1/security/workspaces`
- `GET http://127.0.0.1:8000/api/v1/security/scopes`
- `POST http://127.0.0.1:8000/api/v1/security/scopes`
- `GET http://127.0.0.1:8000/api/v1/security/findings`
- `POST http://127.0.0.1:8000/api/v1/security/static-review`
- `POST http://127.0.0.1:8000/api/v1/security/samples/inspect`
- `GET http://127.0.0.1:8000/api/v1/research/status`
- `GET http://127.0.0.1:8000/api/v1/research/history`
- `POST http://127.0.0.1:8000/api/v1/research/run`
- `POST http://127.0.0.1:8000/api/v1/research/retrieve`
- `POST http://127.0.0.1:8000/api/v1/intelligence/route`
- `GET http://127.0.0.1:8000/api/v1/intelligence/model-profiles`
- `GET http://127.0.0.1:8000/api/v1/prompts/profiles`
- `POST http://127.0.0.1:8000/api/v1/prompts/generate`
- `GET http://127.0.0.1:8000/api/v1/evaluations/datasets`
- `GET http://127.0.0.1:8000/api/v1/evaluations/runs`
- `POST http://127.0.0.1:8000/api/v1/evaluations/run`
- `GET http://127.0.0.1:8000/api/v1/learning/overview`
- `GET http://127.0.0.1:8000/api/v1/learning/blueprints/direct-expert`
- `POST http://127.0.0.1:8000/api/v1/learning/blueprints/direct-expert/import`
- `GET http://127.0.0.1:8000/api/v1/learning/examples`
- `POST http://127.0.0.1:8000/api/v1/learning/examples`
- `GET http://127.0.0.1:8000/api/v1/learning/datasets`
- `POST http://127.0.0.1:8000/api/v1/learning/datasets`
- `GET http://127.0.0.1:8000/api/v1/learning/training/backends`
- `POST http://127.0.0.1:8000/api/v1/learning/training/preflight`
- `GET http://127.0.0.1:8000/api/v1/learning/training/datasets/{dataset_version_id}/export`
- `GET http://127.0.0.1:8000/api/v1/learning/training/jobs`
- `POST http://127.0.0.1:8000/api/v1/learning/training/jobs`
- `GET http://127.0.0.1:8000/api/v1/learning/training/jobs/{job_id}`
- `POST http://127.0.0.1:8000/api/v1/learning/training/jobs/{job_id}/cancel`
- `POST http://127.0.0.1:8000/api/v1/learning/training/jobs/{job_id}/resume`
- `GET http://127.0.0.1:8000/api/v1/learning/models`
- `GET http://127.0.0.1:8000/api/v1/learning/models/{artifact_id}`
- `POST http://127.0.0.1:8000/api/v1/learning/models/{artifact_id}/promote`
- `POST http://127.0.0.1:8000/api/v1/learning/models/{artifact_id}/evaluate`
- `POST http://127.0.0.1:8000/api/v1/learning/models/{artifact_id}/reject`
- `DELETE http://127.0.0.1:8000/api/v1/learning/models/{artifact_id}`
- `GET http://127.0.0.1:8000/api/v1/diagnostics/metrics`
- `GET http://127.0.0.1:8000/api/v1/diagnostics/export`

## Native Local Runtime

The native launcher is stdlib-only and resolves paths from the script location, so it works from the wrong current directory:

```powershell
python scripts/hackergpt.py doctor
python scripts/hackergpt.py start
python scripts/hackergpt.py status
python scripts/hackergpt.py stop
python scripts/hackergpt.py backup
```

`start` runs migrations, starts the FastAPI production server on localhost, waits with bounded probes, and serves the built frontend from `frontend/dist` when available. It never downloads models. `restore` only accepts archive paths under `data/databases/`, `data/knowledge/`, and `config/`.

Windows one-click wrappers are available at `scripts/start-hackergpt.cmd` and `scripts/stop-hackergpt.cmd`.

## Frontend Development

PowerShell on this machine may block `npm.ps1`, so prefer `npm.cmd`:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

The frontend defaults to `http://127.0.0.1:8000` for the backend. Override with:

```powershell
$env:VITE_HACKERGPT_API_BASE_URL="http://127.0.0.1:8000"
```

Open `http://127.0.0.1:5173`.

For production local serving:

```powershell
cd frontend
npm.cmd run build
cd ..
python scripts/hackergpt.py start
```

Open `http://127.0.0.1:8000`.

## Model Providers

Provider configuration lives in `config/models.yaml`. Ollama is enabled by default at `http://127.0.0.1:11434`; llama.cpp, OpenAI-compatible, and vLLM-compatible endpoints are configured but disabled by default. The browser never calls these model endpoints directly; it streams through the HackerGPT backend.

Model routing profiles live in `config/model-profiles/*.yaml`. The router is deterministic, local-first, hardware-aware, and policy-bound. Manual model/provider choices are preserved when explicitly supplied, including local models that have not appeared in discovery yet.

Ollama checks:

```powershell
ollama --version
ollama list
ollama ps
Invoke-WebRequest http://127.0.0.1:11434/api/version
```

Optional real Ollama smoke test:

```powershell
$env:HACKERGPT_RUN_OLLAMA_INTEGRATION="1"
python -m pytest tests/integration/test_ollama_smoke.py
```

No command downloads models automatically.

## Database Migrations

Run migrations:

```powershell
python -m alembic upgrade head
```

Phase 6 adds `0002_streaming_persistent_chat`, which stores generation IDs, generation status, provider/model provenance, idempotency keys, token counts, latency metrics, and indexes for conversation/message access.

Phase 7/8 adds `0003_rag_memory`, which stores documents, chunks, ingestion jobs, embedding cache entries, message retrieval provenance, long-term memories, and memory audit events.

Phase 9/10 adds `0004_agents_tools`, which stores custom agents, tool executions, and confirmation records.

Phase 11/12 adds `0005_security_research`, which stores security workspaces, authorized scopes, findings, notes, research sessions, research sources, and research cache entries.

Phase 13/14 adds no database migration.

Phase 15/16 adds no SQL migration. Evaluation runs and Learning Studio metadata are file-backed under `data/` for this release candidate.

The RC closure auth pass adds `0006_local_auth`, which stores bootstrap username, password hash,
role, and auth metadata on the local user row. Runtime response preferences use the existing
`settings` table.

Create a future migration after model changes:

```powershell
python -m alembic revision --autogenerate -m "describe change"
```

## Quality Checks

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy backend tests
python -m pytest
cd frontend
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test
npm.cmd run build
cd ..
python scripts/smoke_startup.py
python scripts/hackergpt.py doctor
python scripts/benchmark.py --iterations 3 --json-output data/benchmarks/phase15-16-baseline.json --markdown-output docs/performance-baseline.md
```

`make check` runs lint, typecheck, and tests where `make` is available.

## Architecture Summary

Business logic lives in services and repositories, not route handlers. The FastAPI layer validates requests, delegates to services, and serializes Pydantic responses. Persistence is isolated behind SQLAlchemy repositories so SQLite can later be replaced by PostgreSQL without rewriting application logic.

Streaming chat uses server-sent events from a POST request so the frontend can send JSON request bodies and abort via `AbortController`. The backend creates the user and assistant message rows before generation, checkpoints assistant text periodically, and finalizes status and metrics at completion, cancellation, interruption, or failure. It does not write one row per token.

Configuration is loaded from safe defaults, optional YAML, `.env`, and environment variables, with environment variables winning. Policy is separate from model/runtime code and defaults to local-first, cloud-disabled behavior.

RAG ingestion is controlled by `rag_policy` in `config/policy.yaml`. The default embedding provider is deterministic local hashing so document text and queries do not leave the machine. The local FAISS-style store persists JSON vectors under the configured knowledge data directory; the Qdrant adapter is available when a local or explicitly configured Qdrant endpoint is enabled.

Long-term memory is explicit: the user saves, searches, patches, deletes, or exports memory through backend APIs and the Memory page. Automatic memory creation and summaries are disabled by default.

Agents are selected explicitly through the chat selector or Agents page. Built-in agents live in `config/agents/*.yaml`; custom agents are stored in SQLite and can be duplicated, edited, disabled, or deleted when they are not built-in. Agent prompts, model preferences, RAG settings, memory settings, and tool allowlists are subordinate to `config/policy.yaml`.

Tools execute through `ToolRegistry`, `PermissionService`, confirmation records, and persisted audit rows. Read-only tools may auto-run when policy allows. Local writes require confirmation by default. High-impact and shell-mode operations are confirmation-gated or denied by policy. Tool output is truncated, secret-redacted where possible, and stored as untrusted data.

Ethical Hacking workspaces store user-authorized scopes, findings, notes, and exports. Static review is read-only and scans repository text for common weakness patterns. Sample inspection extracts hashes and printable strings without execution. Stable internal `/api/v1/security` APIs and `/cybersecurity` compatibility route remain supported.

Live research is disabled by default. When enabled in `config/policy.yaml`, the backend can query a configured SearxNG endpoint and retrieve HTTP(S) pages through allow/block lists, private-network blocking, byte limits, redirect limits, and cache TTLs. Research sources are stored as citations and untrusted data.

The intelligence engine lives in `backend/intelligence`. `ModelRouter` ranks provider-independent `NormalizedModel` records against task category, agent preference, capability profile, policy, locality, context requirements, and hardware fit. `ContextEngine` replaces ad hoc chat context assembly with token-budgeted, provenance-tagged context items. Prompt Architect lives in `backend/prompting` and `backend/services/prompt_architect.py`; profiles are YAML-backed and can grow by domain without browser-side provider coupling.

The FastAPI application can serve the production frontend build directly. `HACKERGPT_SERVE_FRONTEND=false` disables this behavior, and `HACKERGPT_FRONTEND_DIST_DIR` can point to a custom build directory.

Runtime user preferences are stored locally through `/api/v1/preferences`. They can change response
mode, technical depth, default agent, router bias, and theme, but cannot change trusted execution
policy, tool permissions, network controls, path controls, scopes, confirmations, or audit behavior.

Phase 15/16 adds deterministic evaluation and learning services. `EvaluationService` loads YAML suites from `config/evals` and stores local run records under `data/evaluations`. `LearningService` stores examples, dataset versions, training job metadata, schedules, and model artifacts under `data/learning`. Real model training is optional, explicit, subprocess-based, and available through the `transformers-peft` backend when `.[training]` dependencies and local model files are present. It never executes fine-tuning inline, never runs dataset code, and never promotes artifacts automatically.

Diagnostics are local and sanitized. They include application, hardware, configuration category, path, and aggregate request metric data while excluding secrets, prompts, documents, retrieved chunks, and tool outputs.

Windows notes: prefer `npm.cmd` when PowerShell blocks `npm.ps1`; do not assume a Codex execution workspace can reach host-local `127.0.0.1` services; shell mode is disabled by policy unless explicitly changed.

All content from repositories, documents, web pages, retrieved chunks, memories, model output, terminal output, and tools is treated as data rather than trusted instructions.

Model output is returned as untrusted text only. It cannot execute commands, write files, trigger tools, or change settings.
