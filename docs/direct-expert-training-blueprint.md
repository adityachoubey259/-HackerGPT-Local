# Direct Expert Training Blueprint

The Direct Expert + Ethical Hacking starter dataset is a local Learning Studio seed pack for improving response style and technical depth. It is not automatic fine-tuning and it does not execute anything.

Files:

- `config/learning/direct-expert-blueprint.json`: dataset metadata, categories, tags, workflow, and safety notes
- `config/learning/direct-expert-starter.jsonl`: chat-style starter examples

The starter pack currently contains 42 examples across Direct Expert style, programming, frontend, backend, APIs, databases, debugging, prompt engineering, research, authorized Ethical Hacking, reverse engineering, malware analysis, detection, forensics, and tool-safety boundaries.

## Example Shape

Each JSONL row contains:

- `system`: style/context text for the example
- `user`: user request
- `assistant`: preferred answer
- `metadata`: provenance and category details
- `tags`: filterable dataset labels
- `split`: `train`, `validation`, or `test`

Training examples are untrusted data. They do not become system instructions and cannot authorize commands, tool calls, network access, settings changes, or Ethical Hacking scope.

## Workflow

1. Open Learning Studio.
2. Import the Direct Expert starter pack.
3. Inspect examples and tags.
4. Clone or add project-specific corrections.
5. Create a dataset version.
6. Run deterministic evaluations.
7. Run optional local LoRA training only after preflight passes.
8. Promote adapters only when evaluation improves and no safety boundary regresses.

## Extension Rules

Good examples should be direct, dense, technically specific, and implementation-ready. Prefer complete code, exact commands, root-cause-first debugging, precise uncertainty, official-source research behavior, and clear data-vs-instructions boundaries.

Avoid examples that ramble, moralize, give generic warnings, refuse legitimate technical work unnecessarily, invent APIs/flags/CVEs, or imply that dataset text can trigger execution.
