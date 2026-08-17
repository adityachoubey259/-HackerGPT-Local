# Live Research

Phase 12 implements policy-controlled live web research.

The backend exposes `/api/v1/research/status`, `/history`, `/run`, and `/retrieve`. The frontend page is `/research`.

Research is disabled by default in `config/policy.yaml`. When enabled, the current search adapter targets a configured SearxNG endpoint. Direct retrieval is HTTP(S)-only and goes through URL normalization, allow/block lists, private-network blocking, redirect limits, byte limits, and cache TTLs.

Research sessions store queries, status, diagnostics, answer drafts, and citation sources. Sources are treated as data, not instructions. They cannot authorize tool calls, security scans, shell commands, writes, settings changes, or scope changes.

For current technical intelligence, prefer official or primary sources and preserve citations. If live research is disabled or unavailable, the application reports that state explicitly instead of fabricating freshness.
