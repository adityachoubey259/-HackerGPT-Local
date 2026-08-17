# Learning And Training Studio

Learning in HackerGPT Local is intentionally layered:

- RAG learning: documents and chunks are retrieved with citations as untrusted source data.
- Memory learning: explicit user-approved memories are stored locally and injected with provenance.
- Prompt and agent learning: curated prompts, agent preferences, and context strategies are configured and audited.
- Model training: dataset versions, training-job metadata, and adapter artifacts are tracked locally.

These layers are not interchangeable. A saved memory is not fine-tuning. A retrieved document is not a system prompt. A training artifact is not promoted automatically.

## Data Safety

Training examples, documents, corrections, logs, and generated answers are untrusted data. They may be useful evidence, but they do not authorize commands, settings changes, tool calls, Ethical Hacking scope, or network access.

The backend never executes notebooks, scripts, dataset commands, or model output from training data.

## Dataset Versioning

Learning examples can be split into train, validation, and test sets. Dataset versions record:

- selected example IDs
- split counts
- validation errors
- checksum
- creation time

Validation errors are surfaced when a dataset has no examples, no train examples, or no validation examples.

## Direct Expert Starter Pack

Learning Studio includes an importable Direct Expert + Ethical Hacking starter blueprint:

- metadata: `config/learning/direct-expert-blueprint.json`
- examples: `config/learning/direct-expert-starter.jsonl`
- guide: `docs/direct-expert-training-blueprint.md`

The starter pack is intended for response-style and technical-depth improvement: answer-first behavior, complete code, exact commands, root-cause debugging, precise uncertainty, research-first current facts, and authorized Ethical Hacking lab methodology. Importing the pack creates ordinary local learning examples and a dataset version; it does not launch training.

## Training Jobs

The built-in FastAPI service creates auditable job records and launches real training only when
the user explicitly selects the optional worker path. Metadata-only jobs remain available for
release workflow testing and artifact registry operations.

The first real backend is `transformers-peft`, exposed through a provider-independent
`BaseTrainingBackend` contract. It supports small LoRA adapter experiments through an isolated
subprocess and requires optional dependencies:

```powershell
pip install -e ".[training]"
```

Core installation does not install PyTorch, Transformers, PEFT, Datasets, Accelerate, CUDA, ROCm,
or vector database runtimes. QLoRA/quantized training is not exposed until the backend implements
and verifies quantized model loading honestly.

The worker:

- runs outside the request path
- writes status/progress/checkpoint metadata to local job files
- supports cancellation through a cancel-request file
- supports resume when a checkpoint path is available
- writes safe artifact metadata back through trusted APIs
- never executes untrusted training-data instructions
- saves adapters with safe serialization when supported
- calculates artifact checksums
- refuses implicit remote-code trust

The worker uses `local_files_only=True` when loading tokenizer and model files. A Hub-style model
ID will not be downloaded automatically; place model files locally or populate the cache through an
explicit user-approved process before launching training.

## Preflight

Training preflight exports the selected dataset to JSONL, inspects the current hardware report,
checks optional backend availability, and returns one of:

- `recommended`
- `possible`
- `slow`
- `unlikely_to_fit`
- `unsupported`

The result includes dataset counts, token estimates, validation errors, warnings, hardware markers,
and the resolved preset. It is intentionally conservative on Windows laptops and CPU-only systems.
Tiny datasets are allowed for smoke testing but reported as unsuitable for quality tuning.

## Artifact Layout

Worker outputs are stored under local data paths:

- `data/training/datasets/<dataset-version-id>/dataset.chat.jsonl`
- `data/training/jobs/<job-id>/request.json`
- `data/training/jobs/<job-id>/status.json`
- `data/training/jobs/<job-id>/cancel.request`
- `data/models/adapters/<job-id>/adapter/`
- `data/models/adapters/<job-id>/artifact.json`

Artifacts record base model, adapter type, backend ID, dataset version, artifact path, disk usage,
checksums, and status. Promotion and rollback remain explicit user actions.

## Model Registry

Artifacts can be created, evaluated, promoted, rejected, deleted, and rolled back. Promotion is
explicit and auditable. The active artifact pointer does not automatically rewrite provider
configuration or silently replace a model.

Safe serialization formats are preferred for real adapters. Any future loader must treat adapter metadata as data until validated.
