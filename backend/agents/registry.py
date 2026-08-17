"""Configuration-backed agent registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.agents.models import AgentDefinition
from backend.core.policy import PolicyConfig


class AgentRegistryError(ValueError):
    pass


class AgentRegistry:
    def __init__(
        self,
        config_dir: Path = Path("config/agents"),
        *,
        policy: PolicyConfig | None = None,
        known_tools: set[str] | None = None,
    ) -> None:
        self._config_dir = config_dir
        self._policy = policy or PolicyConfig()
        self._known_tools = known_tools or set()
        self._agents: dict[str, AgentDefinition] = {}
        self.reload()

    def reload(self) -> None:
        agents: dict[str, AgentDefinition] = {}
        if self._config_dir.exists():
            for path in sorted(self._config_dir.glob("*.yaml")):
                data = self._read_yaml(path)
                agent = AgentDefinition.model_validate(data | {"built_in": True})
                self._validate_agent(agent, path)
                if agent.id in agents:
                    raise AgentRegistryError(f"Duplicate agent id: {agent.id}")
                agents[agent.id] = self._policy_filter(agent)
        self._agents = agents

    def list(self, *, include_disabled: bool = False) -> list[AgentDefinition]:
        items = list(self._agents.values())
        if not include_disabled:
            items = [agent for agent in items if agent.enabled]
        return sorted(items, key=lambda agent: (agent.metadata.get("order", 100), agent.name))

    def get(self, agent_id: str) -> AgentDefinition:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise AgentRegistryError(f"Unknown agent: {agent_id}")
        if not agent.enabled:
            raise AgentRegistryError(f"Agent is disabled: {agent_id}")
        return agent

    def default(self) -> AgentDefinition:
        if "general" in self._agents and self._agents["general"].enabled:
            return self._agents["general"]
        enabled = self.list()
        if not enabled:
            raise AgentRegistryError("No enabled agents are configured.")
        return enabled[0]

    def _validate_agent(self, agent: AgentDefinition, path: Path) -> None:
        missing = [
            tool
            for tool in agent.allowed_tools
            if self._known_tools and tool not in self._known_tools
        ]
        if missing:
            raise AgentRegistryError(f"{path} references unknown tools: {', '.join(missing)}")

    def _policy_filter(self, agent: AgentDefinition) -> AgentDefinition:
        if not self._policy.agent_permissions.can_execute_tools:
            return agent.model_copy(
                update={
                    "allowed_tools": [],
                    "tool_execution_config": agent.tool_execution_config.model_copy(
                        update={"enabled": False}
                    ),
                }
            )
        return agent

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            loaded: Any = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise AgentRegistryError(f"Agent file must contain a mapping: {path}")
        return loaded
