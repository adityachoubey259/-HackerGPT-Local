# Tools

Phase 10 adds a secure, auditable tool framework.

## Flow

```text
Trusted API request or structured provider tool call
-> ToolRegistry lookup
-> tool schema validation
-> trusted permission classification
-> agent allowlist check
-> global policy check
-> confirmation when required
-> bounded execution
-> normalized ToolResult
-> audit persistence
```

Ordinary model prose, RAG chunks, memory text, terminal output, Git output, and tool output never create tool executions.

## Interfaces

`BaseTool` defines a common async contract with:

- `name`
- `description`
- `input_schema`
- `permission_class`
- `capabilities`
- `validate_input(...)`
- `classify(...)`
- `execute(...)`

`ToolContext` carries trusted execution metadata such as user, conversation, agent, request/generation IDs, working directory, and policy snapshot.

`ToolResult` normalizes status, stdout, stderr, exit code, structured data, duration, truncation, and error fields.

## Permission Classes

- `READ_ONLY`: inspection operations that do not intentionally modify local state.
- `WRITE_LOCAL`: local file or repository modifications.
- `HIGH_IMPACT`: destructive, shell-mode, system-control, or broad-impact operations.
- `NETWORK`: reserved for future web/research tools.

Runtime classification belongs to trusted application code. A request cannot lower its own permission class.

## Confirmation

Requests requiring confirmation are persisted as pending `ToolExecution` and `ToolConfirmation` rows. The exact payload is hashed. Approval rechecks the stored execution, stored payload, and recomputed hash before execution. Stale, altered, or non-pending confirmations are rejected.

## Built-In Tool Families

- Filesystem: list, read, search, atomic write.
- Terminal: argv-mode subprocess execution with shell mode separately controlled by policy.
- Git: read-only status, diff, log, branch listing, and confirmed branch creation.
- Python: snippet execution in a subprocess, gated as local write because code can affect the workspace.

## Bounds

Subprocess tools use async process APIs, configured timeouts, process-tree cleanup where supported, output truncation, and secret redaction. Tool executions do not hold database transactions while subprocesses run.

## Cancellation

The current cancellation API persists a targeted execution as cancelled. Timeout-based process cleanup is implemented for running subprocesses. Live user-triggered cancellation of an already-running subprocess is intentionally conservative and remains bounded by timeout cleanup.
