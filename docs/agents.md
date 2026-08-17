# Agents

Phase 9 introduces configuration-driven agents for HackerGPT Local.

## Registry

`backend/agents/registry.py` loads built-in YAML profiles from `config/agents`. The registry validates:

- unique agent IDs
- typed `AgentDefinition` fields
- referenced tool names when a tool registry is available
- policy filtering when global agent/tool execution is disabled

Built-ins are immutable through the API. Custom agents are stored in SQLite through `custom_agents` and surfaced by `AgentService`.

## Built-Ins

The required built-ins are:

- General Agent
- Coding Agent
- Ethical Hacking Agent, using stable internal ID `cybersecurity` for backward compatibility
- Research Agent, with Phase 12 web-tool limitations called out in prompt/config
- Document Agent
- Linux Agent
- Data Analysis Agent
- Debugging Agent

Built-ins can express model preferences, generation defaults, RAG settings, memory settings, context strategy, required model capabilities, and allowed tools.

## Selection

Chat agent selection resolves in this order:

1. explicit `agent_id` in the chat request
2. saved `conversation.agent_id`
3. default enabled agent, normally `general`

The selected agent is persisted on conversations. User text cannot switch agents, enable tools, or bypass confirmation; agent changes happen only through trusted UI/API state.

## Policy Precedence

Prompt composition is layered:

1. application security invariants
2. response mode from `config/policy.yaml`, preferably Direct Expert
3. agent specialization
4. user preferences and selected conversation state
5. task context, memory, RAG, and research data

Agent prompts are trusted configuration, but they remain subordinate to application policy. Retrieved chunks, memories, repository content, tool output, and model output are always untrusted data.

## Context

`ContextEngine` composes context as trusted application invariants, response mode, trusted selected-agent specialization, recent conversation, untrusted memory context, untrusted RAG/research/project context, and the current user message. Memory and RAG context can be disabled per agent, but global policy still wins.

## Custom Agents

The API supports creating, duplicating, editing, disabling, and deleting custom agents. Custom agent configuration is validated through the same typed `AgentDefinition` model before it participates in chat.
