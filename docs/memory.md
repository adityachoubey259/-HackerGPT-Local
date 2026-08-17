# Memory

Phase 8 adds explicit long-term memory.

## Behavior

Users can create, list, search, patch, delete, and export memories. Memories can be scoped to user, project, or conversation context, and include importance, tags, pinning, enabled state, provenance, and optional expiry.

Automatic memory creation and automatic conversation summaries are disabled by default. Model output and documents cannot silently create memory.

## Chat Context

Chat selects relevant enabled memories within a bounded token budget and injects them as untrusted user data with `[M#]` citations. Memory never becomes a system instruction.

## Privacy

Memory remains local in SQLite. External memory embeddings are disabled by central policy unless explicitly enabled in a future phase.
