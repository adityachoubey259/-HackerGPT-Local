"""Deterministic task classification for routing and prompt/context policy."""

from __future__ import annotations

from backend.agents.models import AgentDefinition
from backend.intelligence.models import TaskCategory

AGENT_TASKS: dict[str, TaskCategory] = {
    "coding": TaskCategory.CODING,
    "debugging": TaskCategory.DEBUGGING,
    "research": TaskCategory.RESEARCH,
    "cybersecurity": TaskCategory.CYBERSECURITY,
    "data-analysis": TaskCategory.DATA_ANALYSIS,
    "document": TaskCategory.DOCUMENT,
    "linux": TaskCategory.DEVOPS,
}


KEYWORD_TASKS: tuple[tuple[TaskCategory, tuple[str, ...]], ...] = (
    (TaskCategory.FRONTEND, ("react", "css", "tailwind", "vite", "component", "frontend")),
    (TaskCategory.BACKEND, ("fastapi", "django", "api server", "backend", "database transaction")),
    (TaskCategory.API_DESIGN, ("openapi", "rest api", "graphql", "grpc", "webhook", "sse")),
    (TaskCategory.SDK_DEVELOPMENT, ("sdk", "client library", "typed client")),
    (TaskCategory.DATABASE, ("postgres", "sqlite", "sql", "indexing", "migration", "query plan")),
    (TaskCategory.DEVOPS, ("docker", "kubernetes", "ci", "deploy", "terraform", "ansible")),
    (TaskCategory.DEBUGGING, ("traceback", "stack trace", "bug", "debug", "fails", "exception")),
    (TaskCategory.CYBERSECURITY, ("cve", "vulnerability", "threat", "xss", "sql injection")),
    (TaskCategory.REVERSE_ENGINEERING, ("reverse engineer", "decompile", "disassemble", "ghidra")),
    (TaskCategory.MALWARE_ANALYSIS, ("malware", "yara", "sandbox", "ioc", "sample hash")),
    (TaskCategory.RESEARCH, ("latest", "current", "release notes", "documentation", "advisory")),
    (
        TaskCategory.PROMPT_ENGINEERING,
        ("prompt", "system prompt", "agent prompt", "structured output"),
    ),
    (TaskCategory.LONG_CONTEXT, ("entire project", "whole repo", "large context", "long context")),
    (TaskCategory.TOOL_USE, ("run command", "execute", "tool", "terminal", "git diff")),
    (TaskCategory.CODING, ("implement", "code", "refactor", "function", "class", "tests")),
    (TaskCategory.SYSTEM_DESIGN, ("architecture", "system design", "scalability", "tradeoff")),
    (TaskCategory.DATA_ANALYSIS, ("dataframe", "analyze data", "csv", "statistics", "chart")),
    (TaskCategory.DOCUMENT, ("write docs", "summarize", "documentation", "readme")),
)


def classify_task(
    message: str,
    *,
    explicit: TaskCategory | None = None,
    agent: AgentDefinition | None = None,
) -> TaskCategory:
    if explicit is not None:
        return explicit
    if agent is not None and agent.id in AGENT_TASKS:
        return AGENT_TASKS[agent.id]
    lowered = message.lower()
    for task, keywords in KEYWORD_TASKS:
        if any(keyword in lowered for keyword in keywords):
            return task
    if "why" in lowered or "reason" in lowered or "compare" in lowered:
        return TaskCategory.REASONING
    return TaskCategory.GENERAL


def is_version_sensitive(task: TaskCategory, message: str) -> bool:
    lowered = message.lower()
    if task in {TaskCategory.RESEARCH, TaskCategory.CYBERSECURITY, TaskCategory.DEVOPS}:
        return True
    return any(
        keyword in lowered
        for keyword in (
            "latest",
            "current",
            "today",
            "release",
            "version",
            "sdk",
            "api",
            "cve",
            "advisory",
        )
    )
