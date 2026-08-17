# Model Routing

Phase 13 adds a provider-independent router in `backend/intelligence`.

## Goals

- Keep local-first behavior as the default.
- Preserve explicit manual provider/model selection.
- Rank discovered models by task, policy, agent preference, capability profile, and hardware fit.
- Avoid silent fallback from local providers to remote or cloud endpoints.
- Report diagnostics as data so the UI can explain routing decisions.

## Flow

1. `TaskClassifier` maps the user request and active agent to a `TaskCategory`.
2. `ModelProfileRegistry` loads YAML profiles from `config/model-profiles/*.yaml`.
3. `ModelRouter` filters provider/model candidates by provider health, capability requirements, locality, router mode, and policy.
4. Candidates are scored by local provider status, agent preference, profile strength, hardware fit, context requirements, and speed/quality mode.
5. The selected route is passed to chat generation unless the request supplied an explicit provider and model.

Manual routing is intentionally permissive for configured local providers. If a user selects a model that has not appeared in discovery yet, the router preserves that choice and records a diagnostic instead of replacing it.

## Router Modes

- `manual`: require `manual_provider` and `manual_model`.
- `auto`: balanced local-first selection.
- `local_only`: reject non-local endpoints.
- `quality_first`: prefer stronger reasoning/coding profiles.
- `speed_first`: prefer faster profiles.
- `low_memory`: prefer models with excellent or good hardware fit.

## Policy

`config/policy.yaml` remains authoritative. When `model_routing.cloud_fallback_enabled` is false, non-local candidates are removed even if configured. Model output and routing diagnostics are untrusted data and cannot trigger tools or settings changes.
