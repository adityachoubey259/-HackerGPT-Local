"""Agent API schemas."""

from __future__ import annotations

from backend.agents.models import AgentCreate, AgentDefinition, AgentPatch

AgentRead = AgentDefinition
AgentCreateRequest = AgentCreate
AgentPatchRequest = AgentPatch
