from __future__ import annotations

import sys
from pathlib import Path
from shutil import which

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.agents.registry import AgentRegistry, AgentRegistryError
from backend.api.errors import ApplicationError
from backend.core.policy import AgentPermissionsPolicy, CommandPolicy, PolicyConfig
from backend.db.models import ToolConfirmation
from backend.services.agents import AgentService
from backend.services.tools import ToolService
from backend.tools.builtins import TerminalRunTool, build_builtin_tools
from backend.tools.models import PermissionClass, ToolContext, ToolStatus
from backend.tools.registry import ToolRegistry
from backend.tools.safety import ToolSafetyError, resolve_tool_path

REPO_ROOT = Path(__file__).resolve().parents[2]


def permissive_test_policy(*, timeout_seconds: int = 5) -> PolicyConfig:
    return PolicyConfig(
        command_execution=CommandPolicy(
            default_timeout_seconds=timeout_seconds,
            maximum_timeout_seconds=max(timeout_seconds, 2),
            output_limit_bytes=4096,
            allowed_tool_roots=["."],
        ),
        agent_permissions=AgentPermissionsPolicy(enabled=True, can_execute_tools=True),
    )


def tool_service(
    session_factory: async_sessionmaker[AsyncSession],
    workspace_root: Path,
    *,
    timeout_seconds: int = 5,
) -> ToolService:
    policy = permissive_test_policy(timeout_seconds=timeout_seconds)
    registry = ToolRegistry(build_builtin_tools(policy, workspace_root))
    agents = AgentRegistry(
        REPO_ROOT / "config" / "agents",
        policy=policy,
        known_tools=registry.names(),
    )
    return ToolService(
        session_factory,
        policy,
        registry,
        AgentService(session_factory, agents),
        workspace_root=workspace_root,
    )


def write_agent_config(directory: Path, name: str, agent_id: str, tools: list[str]) -> None:
    lines = [
        f"id: {agent_id}",
        f"name: {agent_id.title()} Agent",
        "description: Test agent",
        "system_prompt: Keep test behavior safe.",
    ]
    if tools:
        lines.extend(["allowed_tools:", *[f"  - {tool}" for tool in tools]])
    directory.joinpath(name).write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def test_agent_registry_loads_required_builtins() -> None:
    policy = permissive_test_policy()
    registry = AgentRegistry(REPO_ROOT / "config" / "agents", policy=policy)
    ids = {agent.id for agent in registry.list()}

    assert {
        "general",
        "coding",
        "expert",
        "cybersecurity",
        "research",
        "document",
        "linux",
        "data-analysis",
        "debugging",
    }.issubset(ids)
    assert registry.default().id == "general"


def test_agent_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    write_agent_config(tmp_path, "one.yaml", "duplicate", [])
    write_agent_config(tmp_path, "two.yaml", "duplicate", [])

    with pytest.raises(AgentRegistryError, match="Duplicate agent id"):
        AgentRegistry(tmp_path)


def test_agent_registry_rejects_unknown_tool_reference(tmp_path: Path) -> None:
    write_agent_config(tmp_path, "agent.yaml", "limited", ["filesystem.read", "missing.tool"])

    with pytest.raises(AgentRegistryError, match="unknown tools"):
        AgentRegistry(tmp_path, known_tools={"filesystem.read"})


def test_agent_registry_policy_filters_tools_when_disabled() -> None:
    policy = PolicyConfig(
        agent_permissions=AgentPermissionsPolicy(enabled=True, can_execute_tools=False)
    )
    registry = AgentRegistry(REPO_ROOT / "config" / "agents", policy=policy)

    assert registry.get("coding").allowed_tools == []
    assert not registry.get("coding").tool_execution_config.enabled


def test_path_security_rejects_outside_and_symlink_escape(tmp_path: Path) -> None:
    policy = permissive_test_policy()
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    inside = resolve_tool_path(tmp_path, policy, "nested/new-file.txt")

    assert inside == tmp_path / "nested" / "new-file.txt"
    with pytest.raises(ToolSafetyError, match="outside configured tool roots"):
        resolve_tool_path(tmp_path, policy, "../outside.txt")
    with pytest.raises(ToolSafetyError, match="outside configured tool roots"):
        resolve_tool_path(tmp_path, policy, str(outside))

    outside.write_text("escape", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this execution environment.")
    with pytest.raises(ToolSafetyError, match="outside configured tool roots"):
        resolve_tool_path(tmp_path, policy, "link.txt")


def test_terminal_classifies_permission_from_trusted_logic(tmp_path: Path) -> None:
    tool = TerminalRunTool(permissive_test_policy(), tmp_path)

    assert tool.classify(tool.validate_input({"argv": ["python", "--version"]})) == (
        PermissionClass.READ_ONLY
    )
    assert tool.classify(tool.validate_input({"argv": ["mkdir", "local-dir"]})) == (
        PermissionClass.WRITE_LOCAL
    )
    assert tool.classify(tool.validate_input({"argv": ["rm", "-rf", "anything"]})) == (
        PermissionClass.HIGH_IMPACT
    )
    assert tool.classify(tool.validate_input({"argv": ["echo", "ok"], "shell": True})) == (
        PermissionClass.HIGH_IMPACT
    )


async def test_terminal_argv_does_not_interpret_shell_metacharacters(tmp_path: Path) -> None:
    tool = TerminalRunTool(permissive_test_policy(), tmp_path)
    payload = tool.validate_input(
        {
            "argv": [
                sys.executable,
                "-c",
                "import sys; print(sys.argv[1])",
                "literal; && | > $() ` quoted",
            ],
            "cwd": ".",
        }
    )
    result = await tool.execute(make_context(tmp_path), payload, execution_id="exec-argv")

    assert result.status == ToolStatus.COMPLETED
    assert result.stdout is not None
    assert result.stdout.strip() == "literal; && | > $() ` quoted"


async def test_subprocess_timeout_keeps_partial_output(tmp_path: Path) -> None:
    tool = TerminalRunTool(permissive_test_policy(timeout_seconds=1), tmp_path)
    payload = tool.validate_input(
        {
            "argv": [
                sys.executable,
                "-c",
                "import time; print('started', flush=True); time.sleep(5)",
            ],
            "cwd": ".",
            "timeout_seconds": 1,
        }
    )
    result = await tool.execute(make_context(tmp_path), payload, execution_id="exec-timeout")

    assert result.status == ToolStatus.TIMED_OUT
    assert result.error_code == "TOOL_TIMEOUT"
    assert result.stdout is not None
    assert "started" in result.stdout


async def test_tool_service_requires_confirmation_and_rejects_tampering(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    service = tool_service(session_factory, tmp_path)
    response = await service.execute(
        tool_name="filesystem.write",
        arguments={"path": "created.txt", "content": "original"},
        agent_id="coding",
        conversation_id=None,
        request_id="request-1",
    )
    assert response.confirmation is not None
    assert response.execution.status == ToolStatus.PENDING_CONFIRMATION

    async with session_factory() as session:
        confirmation = await session.scalar(
            select(ToolConfirmation).where(ToolConfirmation.id == response.confirmation.id)
        )
        assert confirmation is not None
        tampered_payload = dict(confirmation.payload)
        tampered_payload["arguments"] = {"path": "created.txt", "content": "tampered"}
        confirmation.payload = tampered_payload
        await session.commit()

    with pytest.raises(ApplicationError, match="Stored confirmation payload does not match"):
        await service.approve(response.confirmation.id)
    assert not tmp_path.joinpath("created.txt").exists()


async def test_tool_service_approves_exact_write_and_records_history(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    service = tool_service(session_factory, tmp_path)
    response = await service.execute(
        tool_name="filesystem.write",
        arguments={"path": "created.txt", "content": "approved"},
        agent_id="coding",
        conversation_id=None,
        request_id="request-2",
    )
    assert response.confirmation is not None
    execution, confirmation = await service.approve(response.confirmation.id)
    history = await service.history(limit=10, offset=0)

    assert confirmation.status == "approved"
    assert execution.status == ToolStatus.COMPLETED
    assert tmp_path.joinpath("created.txt").read_text(encoding="utf-8") == "approved"
    assert history.total == 1


async def test_python_tool_executes_after_confirmation(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    service = tool_service(session_factory, tmp_path)
    response = await service.execute(
        tool_name="python.run",
        arguments={"code": "print(6 * 7)", "timeout_seconds": 2},
        agent_id="coding",
        conversation_id=None,
        request_id="request-python",
    )
    assert response.confirmation is not None
    execution, _ = await service.approve(response.confirmation.id)

    assert execution.status == ToolStatus.COMPLETED
    assert execution.stdout is not None
    assert execution.stdout.strip() == "42"


async def test_tool_service_cancel_persists_status(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    service = tool_service(session_factory, tmp_path)
    response = await service.execute(
        tool_name="filesystem.write",
        arguments={"path": "cancelled.txt", "content": "nope"},
        agent_id="coding",
        conversation_id=None,
    )
    cancelled = await service.cancel(response.execution.id)

    assert cancelled.status == ToolStatus.CANCELLED
    assert not tmp_path.joinpath("cancelled.txt").exists()


async def test_git_read_tools_run_against_temp_repository(tmp_path: Path) -> None:
    if which("git") is None:
        pytest.skip("Git executable is unavailable in this execution environment.")
    policy = permissive_test_policy()
    context = make_context(tmp_path)
    setup = TerminalRunTool(policy, tmp_path)
    for index, argv in enumerate(
        [
            ["git", "init"],
            ["git", "config", "user.email", "test@example.invalid"],
            ["git", "config", "user.name", "HackerGPT Test"],
        ],
        start=1,
    ):
        result = await setup.execute(
            context,
            setup.validate_input({"argv": argv, "cwd": "."}),
            execution_id=f"git-setup-{index}",
        )
        assert result.status == ToolStatus.COMPLETED
    tmp_path.joinpath("README.md").write_text("initial\n", encoding="utf-8")
    for index, argv in enumerate(
        [
            ["git", "add", "README.md"],
            ["git", "commit", "-m", "initial"],
        ],
        start=1,
    ):
        result = await setup.execute(
            context,
            setup.validate_input({"argv": argv, "cwd": "."}),
            execution_id=f"git-commit-{index}",
        )
        assert result.status == ToolStatus.COMPLETED
    tmp_path.joinpath("README.md").write_text("changed\n", encoding="utf-8")
    registry = ToolRegistry(build_builtin_tools(policy, tmp_path))

    for tool_name in ("git.status", "git.diff", "git.log", "git.branches"):
        tool = registry.get(tool_name)
        result = await tool.execute(
            context,
            tool.validate_input({"cwd": "."}),
            execution_id=f"exec-{tool_name}",
        )
        assert result.status == ToolStatus.COMPLETED
        assert result.stdout is not None


def make_context(tmp_path: Path) -> ToolContext:
    policy = permissive_test_policy()
    return ToolContext(
        user_id="user-1",
        working_directory=str(tmp_path),
        policy_snapshot=policy.model_dump(mode="json"),
    )
