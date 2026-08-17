"""Centralized tool permission evaluation."""

from __future__ import annotations

from backend.agents.models import AgentDefinition
from backend.core.policy import AccessMode, PolicyConfig
from backend.tools.models import (
    PermissionClass,
    PermissionDecision,
    PermissionDecisionType,
    ToolDefinition,
)


class PermissionService:
    def __init__(self, policy: PolicyConfig) -> None:
        self._policy = policy

    def evaluate(
        self,
        *,
        tool: ToolDefinition,
        classified_permission: PermissionClass,
        agent: AgentDefinition | None,
    ) -> PermissionDecision:
        if not self._policy.command_execution.tools_enabled:
            return deny(classified_permission, "Tools are disabled by policy.")
        if not self._policy.agent_permissions.can_execute_tools:
            return deny(classified_permission, "Agents cannot execute tools by policy.")
        if agent is not None:
            if not agent.tool_execution_config.enabled:
                return deny(classified_permission, "Selected agent has tool execution disabled.")
            if tool.name not in agent.allowed_tools:
                return deny(classified_permission, "Tool is not allowed for the selected agent.")
        if classified_permission == PermissionClass.NETWORK:
            if self._policy.tool_permissions.network_tools != AccessMode.ENABLED:
                return deny(classified_permission, "Network tools are disabled in this phase.")
        if (
            tool.name.startswith("terminal.")
            and not self._policy.command_execution.terminal_enabled
        ):
            return deny(classified_permission, "Terminal tools are disabled by policy.")
        if tool.name.startswith("git.") and not self._policy.command_execution.git_enabled:
            return deny(classified_permission, "Git tools are disabled by policy.")
        if tool.name.startswith("python.") and not self._policy.command_execution.python_enabled:
            return deny(classified_permission, "Python tools are disabled by policy.")
        if (
            tool.name == "terminal.run"
            and "shell" in tool.capabilities
            and not self._policy.command_execution.shell_mode_enabled
        ):
            # The tool checks the actual argument too; this keeps shell mode visible in policy.
            pass
        if self._policy.command_execution.always_confirm:
            return confirm(classified_permission, "Policy requires confirmation for all tools.")
        if classified_permission == PermissionClass.READ_ONLY:
            if self._policy.command_execution.read_only_auto_execute:
                return allow(classified_permission, "Read-only tool auto-allowed by policy.")
            return confirm(classified_permission, "Read-only tools require confirmation by policy.")
        if classified_permission == PermissionClass.WRITE_LOCAL:
            if self._policy.command_execution.write_local_requires_confirmation:
                return confirm(classified_permission, "Local write requires confirmation.")
            return allow(classified_permission, "Local write allowed by policy.")
        return confirm(classified_permission, "High-impact operation requires confirmation.")


def allow(permission: PermissionClass, reason: str) -> PermissionDecision:
    return PermissionDecision(
        decision=PermissionDecisionType.ALLOW,
        permission_class=permission,
        reason=reason,
        risk_level="low" if permission == PermissionClass.READ_ONLY else "medium",
        risk_summary=reason,
    )


def confirm(permission: PermissionClass, reason: str) -> PermissionDecision:
    return PermissionDecision(
        decision=PermissionDecisionType.REQUIRE_CONFIRMATION,
        permission_class=permission,
        reason=reason,
        risk_level="high" if permission == PermissionClass.HIGH_IMPACT else "medium",
        risk_summary=reason,
    )


def deny(permission: PermissionClass, reason: str) -> PermissionDecision:
    return PermissionDecision(
        decision=PermissionDecisionType.DENY,
        permission_class=permission,
        reason=reason,
        risk_level="blocked",
        risk_summary=reason,
    )
