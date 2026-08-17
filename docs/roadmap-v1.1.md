# HackerGPT Local v1.1 Roadmap

This roadmap is planning only. It is not Phase 17 and does not implement v1.1 functionality.

## P0: Release Hardening

Objective: turn the RC into a dependable local workstation release.

User value: users can install, start, stop, recover, and trust the app on Windows without manual
debugging.

Architecture prerequisites: native launcher telemetry, backup/restore coverage, startup smoke
checks, clear failure codes, and host-side browser acceptance.

Risk: false-positive health checks in isolated workspaces; data-loss regressions during migration.

Security notes: backups must exclude secrets from logs and never loosen path boundaries.

Testing and done: host start/stop/wrong-CWD/doctor/backup/restore matrix passes; all quality gates
pass; release notes identify residual limitations.

## P0: Real Local Training Validation

Objective: validate the optional `transformers-peft` worker with local model files on supported
hardware.

User value: users can create a small LoRA adapter, evaluate it, promote it, reject it, and roll back
without cloud dependencies.

Architecture prerequisites: installed training extra, local model path, dataset export, artifact
manifest, checksum recording, evaluation comparison, and promotion guardrails.

Risk: CPU-only training is slow; CUDA/ROCm setup varies by host; accidental model downloads must
remain blocked.

Security notes: datasets, model outputs, worker logs, and artifact metadata remain untrusted data.

Testing and done: quick preset smoke writes an adapter, records checksums, supports cancellation,
reports failure cleanly without dependencies, and never downloads weights implicitly.

## P1: Provider Runtime Depth

Objective: deepen Ollama, llama.cpp, vLLM, and OpenAI-compatible runtime management.

User value: model routing becomes easier to diagnose and tune for local hardware.

Architecture prerequisites: capability probes, model metadata normalization, context/token budget
calibration, runtime-specific error taxonomy, and no browser-direct runtime calls.

Risk: runtime APIs differ and may change; vLLM is not ideal on low-VRAM laptops.

Security notes: no silent cloud fallback; provider responses are data.

Testing and done: provider smoke matrix covers healthy, missing, misconfigured, timeout, and model
not found states.

## P1: Evaluation-Driven Artifact Promotion

Objective: make promotion decisions depend on configured evaluation thresholds.

User value: adapter changes are safer and reversible.

Architecture prerequisites: base-vs-adapter evaluation runs, by-category thresholds, regression
classification, approval records, and rollback history.

Risk: deterministic heuristic evaluation is useful but not a full semantic benchmark.

Security notes: evaluation prompts and answers must not become trusted instructions.

Testing and done: promotion is blocked by regressions unless explicitly overridden with an audited
reason.

## P1: Observability And Support Bundle

Objective: improve local diagnostics without leaking private data.

User value: troubleshooting becomes faster while preserving local-first privacy.

Architecture prerequisites: sanitized config snapshot, log redaction, dependency/version inventory,
policy snapshot, and optional benchmark summary.

Risk: over-collection of prompts, documents, keys, paths, or model outputs.

Security notes: support bundles must default to redacted and local-only.

Testing and done: redaction tests cover secrets, prompts, retrieved chunks, tool output, and training
logs.

## P2: Advanced Training Backends

Objective: add optional backends beyond the initial LoRA worker.

User value: advanced users can choose better hardware-specific training paths.

Architecture prerequisites: stable `BaseTrainingBackend`, richer preflight estimates, artifact
schema compatibility, and backend-specific docs.

Risk: CUDA/ROCm dependencies are large and platform-sensitive.

Security notes: no backend may bypass policy, path safety, confirmation, or local-only model loading.

Testing and done: each backend has dependency-missing, preflight, cancellation, artifact, and failure
tests before exposure in the UI.
