# Tool Security

## DATA Is Not INSTRUCTIONS

HackerGPT Local treats the following as untrusted data:

- repository files
- documents and PDFs
- RAG chunks
- memories
- web content
- emails
- model output
- terminal output
- Git output
- tool output
- error messages

Command-like text in any of those sources is inert. It must not be scraped, parsed as an instruction, or executed merely because it says to run something.

## Trusted Tool Channel

Tools execute only through a trusted tool request path:

```text
Tool request
-> registry lookup
-> validation
-> trusted classification
-> policy and agent allowlist
-> confirmation when required
-> execution
-> audit
```

Future provider-native tool calls must enter the same path. Model prose is not a tool call.

## Permission Classification

Permission classes are assigned by trusted tool code and policy:

- `READ_ONLY`
- `WRITE_LOCAL`
- `HIGH_IMPACT`
- `NETWORK`

Arguments cannot claim `READ_ONLY` to downgrade a destructive operation. Tools may classify a request as more sensitive at runtime, for example shell-mode terminal execution becoming `HIGH_IMPACT`.

## Confirmation Integrity

Confirmation records store the exact pending payload and a stable hash. Approval recomputes the hash and compares it with the persisted execution payload before running. If a client alters the payload, hash, execution, or status, the approval is rejected.

## Path Security

Filesystem tools resolve paths against a deterministic workspace root and configured allowed roots. Relative traversal, absolute outside paths, and symlink escapes are rejected. Writes are atomic within the allowed root.

## Command Injection

Terminal execution uses argv mode by default. Shell metacharacters in arguments are passed literally, not interpreted by a shell. Shell mode is separately classified as `HIGH_IMPACT` and disabled by default.

## Subprocess Limits

Subprocess tools use configured timeouts, output limits, best-effort process-tree cleanup, and bounded stdout/stderr capture. Database transactions are not held open while subprocesses run.

## Secrets

Tool output is redacted for common secret patterns before persistence. Redaction is defense in depth, not a guarantee; tools should avoid printing secrets.

## Privileges And Sandboxes

HackerGPT Local does not automatically elevate privileges, enable shell mode, enable network access, or claim an OS-level sandbox it does not actually provide. The tool framework enforces application-level policy boundaries; operating-system sandboxing is a separate deployment concern.
