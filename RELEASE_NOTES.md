# HackerGPT Local Release Notes

## 1.0.0-rc.1

Status: release candidate, not final `1.0.0`.

This RC adds the final local-learning closure work without stamping the final release. The core app
still avoids heavyweight ML dependencies, while optional real LoRA training is now available behind
an explicit `transformers-peft` worker path.

Highlights:

- Added authenticated runtime preferences for response mode, technical depth, default agent, router
  bias, and theme without allowing browser writes to `config/policy.yaml`.
- Wired persisted preferences into chat prompt composition and context diagnostics.
- Added local change-password support with server-side password hashing and password-revision cookie
  invalidation.
- Expanded Settings and command palette controls for runtime Direct Expert switching.
- Added optional `pip install -e ".[training]"` dependencies for Transformers, PEFT, Datasets,
  Accelerate, Safetensors, and Torch.
- Added provider-independent training backend contracts and a Transformers/PEFT LoRA backend.
- Added training preflight with dataset export, hardware fit classification, backend capability
  reporting, and local-model warnings.
- Added an isolated training worker subprocess with progress files, cancellation requests, checkpoint
  resume metadata, adapter manifests, and checksum capture.
- Expanded Learning Studio with backend status, preflight/export details, worker launch controls,
  job progress, cancellation/resume actions, and artifact evaluate/reject/delete controls.
- Preserved metadata-only training records for release workflow testing.
- Kept model output, tool output, retrieved documents, and training data classified as untrusted data.

Final `1.0.0` remains blocked until host-side browser acceptance, real configured provider smoke,
native launcher start/stop/wrong-CWD acceptance, and real local training verification pass on target
hardware.
