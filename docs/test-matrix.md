# v1.0 RC Test Matrix

This matrix tracks local release-candidate validation for HackerGPT Local.

## Backend Gates

| Gate | Command | Expected Result |
| --- | --- | --- |
| Ruff lint | `python -m ruff check .` | No lint errors |
| Ruff format | `python -m ruff format --check .` | No formatting drift |
| mypy | `python -m mypy backend tests` | Strict typing succeeds |
| pytest | `python -m pytest` | Unit and integration tests pass |
| Alembic current | `python -m alembic current` | Reports `0006_local_auth (head)` |
| Startup smoke | `python scripts\smoke_startup.py` | App factory and startup path succeed |

## Frontend Gates

| Gate | Command | Expected Result |
| --- | --- | --- |
| ESLint | `npm.cmd run lint` | No lint errors |
| TypeScript | `npm.cmd run typecheck` | Strict app and node configs succeed |
| Vitest | `npm.cmd run test` | Component and API tests pass |
| Production build | `npm.cmd run build` | Vite emits production assets |

## Release Scenarios

| Area | Coverage |
| --- | --- |
| Evaluation | YAML-backed deterministic suites, run persistence, unknown dataset errors |
| Learning Studio | Example intake, dataset validation, metadata-only jobs, real-worker launch metadata, artifact evaluate/promote/reject/delete/rollback |
| Training | Optional backend capability reporting, dataset JSONL export, preflight warnings, worker manager launch/cancel, interrupted-job recovery |
| Diagnostics | Local metrics and sanitized export with prompts, documents, tool output, and secrets excluded |
| Security | Policy remains central; no keyword-based Ethical Hacking blocking added |
| Runtime | Native launcher backs up local state before migration by default |
| Auth | Bootstrap login/logout/session restore, protected API rejection, password hashing, password change, old-cookie invalidation |
| Preferences | Authenticated response-mode/depth/default-agent/router/theme persistence and validation |
| Direct Expert | Central prompt composition, no blanket refusal, investigate-before-unknown, and execution-control invariants |
| UI | Source-based review for Learning Studio, model registry, eval history, empty/loading states |

## Manual Acceptance Still Required

- Host browser visual acceptance for light/dark themes and narrow windows.
- Real local runtime smoke with the user's configured Ollama, llama.cpp, vLLM, or OpenAI-compatible endpoints.
- Real local training smoke with `pip install -e ".[training]"`, local model files, adapter output, evaluation, promotion, and rollback.
- Native launcher start/stop/wrong-CWD/doctor/backup/restore acceptance on the user's Windows host.
- Optional Docker Compose profile validation on the target host.
