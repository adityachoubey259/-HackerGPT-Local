# Context Engine

Phase 13 moves chat context assembly into `ContextEngine`.

## Inputs

The engine can assemble:

- system prompt
- response mode policy, including Direct Expert behavior
- active agent prompt
- current user request
- recent conversation messages
- explicit long-term memory
- RAG retrievals
- lightweight project context
- policy-enabled live research for version-sensitive requests

## Budgeting

Context is assembled as typed `ContextItem` records with source, role, priority, estimated tokens, citation ID, title, and metadata. The budget keeps a safety margin and reserved output tokens, then trims lower-priority or later-added context first.

Token counts are estimates. The engine favors deterministic bounded behavior over provider-specific tokenizer coupling.

## Provenance

Diagnostics include budget data, included/omitted counts, memory/RAG/web metadata, and source provenance. Retrieved chunks, memory, project files, web pages, terminal output, tool output, and model output remain data, not instructions.

Diagnostics expose response mode and technical depth for UI inspection. They do not expose hidden reasoning.

## Research

Live research is only considered when `policy.research.enabled` is true and the prompt appears version-sensitive. Network access remains controlled by the Phase 11/12 research service and its URL safety checks.
