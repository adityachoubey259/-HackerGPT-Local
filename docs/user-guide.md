# User Guide

## Start Locally

```powershell
python scripts/hackergpt.py doctor
python scripts/hackergpt.py start
```

The launcher runs migrations, creates a pre-migration backup by default, starts the local FastAPI server, and serves the production frontend build when available.

## Login

HackerGPT Local uses a local single-user bootstrap account by default:

- username: `admin`
- password: `admin987`

The password is verified by the backend and stored only as a password hash. The browser receives an httpOnly signed session cookie after login; it does not contain or check the password in client code. Override the bootstrap defaults with `BOOTSTRAP_ADMIN_USERNAME` and `BOOTSTRAP_ADMIN_PASSWORD` or the equivalent `HACKERGPT_` environment settings.

## Core Workspaces

- Chat: streaming local-first conversations through the backend.
- Models: provider health, discovered models, and backend-mediated runtime tests.
- Knowledge: document ingestion, chunks, citations, and local vector search.
- Memory: explicit long-term memories and export.
- Agents: configurable local agents with policy-bound tools and context strategy.
- Tools: audited tool execution, confirmations, and results.
- Ethical Hacking: authorized local lab workspaces, scopes, evidence, findings, notes, and read-only static review. The older `/cybersecurity` route remains supported.
- Research: policy-controlled live research when explicitly enabled.
- Intelligence: model routing and context diagnostics.
- Prompt Lab: deterministic prompt generation and structured-output scaffolds.
- Learning Studio: datasets, Direct Expert starter import, evaluations, training metadata, and model artifact registry.
- System Status: hardware, database, provider, and local runtime diagnostics.

## Privacy Model

The browser calls only HackerGPT backend APIs. Model providers, vector stores, research providers, and future training workers stay server-side and policy-controlled.

Cloud inference and live research remain disabled unless explicitly configured and allowed by policy.

## Response Mode

Direct Expert is the default response profile. It favors answer-first, low-fluff, technically deep responses, complete code when implementation is requested, exact commands when commands are requested, and investigation before declaring unknown. This does not change tool permissions: execution still requires structured tool calls, policy, scope, confirmations, timeouts, path/network controls, and audit logs.

Settings can persist response mode, technical depth, default agent, router bias, and theme through
the backend preferences API. These preferences affect prompt composition and model routing only
inside the safe application bounds from `config/policy.yaml`.

The local account panel supports changing the bootstrap password. The new value is hashed server-side
and old signed cookies are invalidated by password revision.

## Starter Dataset

Learning Studio exposes a Direct Expert + Ethical Hacking starter pack. Importing it creates local examples and a dataset version for evaluation or optional adapter training. The dataset is seed data only; it does not trigger fine-tuning or execute any commands.

## Visual Acceptance

Source-based UI review completed; host-side visual acceptance still required.
