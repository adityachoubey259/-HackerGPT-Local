# Prompt Architect

Prompt Architect turns a user objective into a structured, domain-aware prompt without coupling the browser to model providers.

## Components

- `backend/prompting/models.py`: request/response and profile schemas.
- `backend/prompting/profiles.py`: YAML-backed profile registry.
- `backend/services/prompt_architect.py`: deterministic prompt generation service.
- `frontend/src/pages/PromptLabPage.tsx`: local UI for prompt design.

## Profiles

Profiles live in `config/prompt-profiles/*.yaml` and can define:

- prompt type
- domain and language matches
- default agent
- recommended model capabilities
- required context sources
- checklist items

## Guarantees

Generated prompts include local-first/privacy constraints, the data-versus-instructions boundary, testing and security guidance when requested, and explicit assumptions. JSON output scaffolds are generated only when the requested output format asks for JSON.

The preferred lab/security category is `ethical_hacking_lab`. The older `cybersecurity_lab` type remains as a compatibility profile for existing callers. Ethical Hacking prompts should include role, environment, trusted active scope when available, objective, tools, constraints, expected evidence, validation, and output/report format.

The service does not call an LLM. It prepares prompts for local or explicitly configured model endpoints.
