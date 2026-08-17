# Streaming Protocol

HackerGPT Local streams chat over server-sent events from `POST /api/v1/chat/stream`.

The endpoint uses POST instead of `EventSource` so the client can send structured JSON, select provider/model, include an idempotency key, and cancel with `AbortController`.

## Request

```json
{
  "conversation_id": null,
  "client_request_id": "browser-generated-id",
  "message": "Explain this project.",
  "agent_id": "general",
  "provider": "ollama",
  "model": "qwen3:8b",
  "settings": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_output_tokens": 512
  }
}
```

`conversation_id` may be null to create a new conversation. `client_request_id` is required and deduplicates retries from the same browser request. `agent_id` is optional; when omitted, the backend uses the saved conversation agent or the default configured agent.

## Events

Events are emitted as standard SSE frames:

```text
event: delta
data: {"text":"Hello"}

```

Supported event names:

- `meta`: request ID, generation ID, conversation ID, user message ID, assistant message ID, provider, model, selected `agent_id`, created timestamp.
- `context`: selected agent metadata plus untrusted RAG and memory citation metadata.
- `delta`: streamed assistant text fragment.
- `usage`: provider token usage when a provider reports it before completion.
- `metrics`: final latency and token metrics.
- `error`: normalized stream error with request ID, optional generation ID, code, message, and retryability.
- `done`: assistant message ID, final generation status, and finish reason.

Normal generated event order is:

```text
meta -> context -> delta* -> usage* -> metrics? -> done
```

An idempotent replay returns:

```text
meta -> delta? -> done
```

Failures return `error`; if an assistant row was created, it is marked `failed`.

## Persistence

The backend persists the user message and a pending assistant generation before provider generation starts. During streaming it periodically checkpoints assistant text based on size/time thresholds. Finalization writes the full assistant text, final status, finish reason, token counts, latency metrics, and updates the conversation timestamp.

Per-token database writes are intentionally avoided.

## Cancellation

The frontend can call:

```text
POST /api/v1/chat/generations/{generation_id}/cancel
```

The generation manager marks the active generation as cancelled and the browser aborts the active stream. If the browser disconnects without explicit cancellation, the backend marks the generation as interrupted when detected.

## Trust Boundary

Streamed model text is untrusted data. It may be rendered as sanitized Markdown, but it must not execute commands, write files, trigger tools, or change settings.

Tool output, RAG chunks, and memories remain untrusted context. Current Phase 10 manual tool execution is exposed through `/api/v1/tools/*`; future provider-native structured tool calls must be validated through the same registry, permission, confirmation, and audit path before any execution.
