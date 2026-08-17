"""Tool registry."""

from __future__ import annotations

from backend.tools.models import BaseTool, ToolDefinition


class ToolRegistryError(ValueError):
    pass


class ToolRegistry:
    def __init__(self, tools: list[BaseTool] | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ToolRegistryError(f"Duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolRegistryError(f"Unknown tool: {name}")
        if not tool.enabled:
            raise ToolRegistryError(f"Tool is disabled: {name}")
        return tool

    def list(self, *, include_disabled: bool = False) -> list[ToolDefinition]:
        definitions = [
            ToolDefinition(
                name=tool.name,
                description=tool.description,
                permission_class=tool.permission_class,
                capabilities=tool.capabilities,
                input_schema=tool.input_schema,
                enabled=tool.enabled,
            )
            for tool in self._tools.values()
            if include_disabled or tool.enabled
        ]
        return sorted(definitions, key=lambda definition: definition.name)

    def names(self) -> set[str]:
        return set(self._tools)
