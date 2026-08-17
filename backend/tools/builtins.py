"""Built-in secure tools."""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Any

from backend.core.policy import PolicyConfig
from backend.core.time import utc_now
from backend.tools.models import BaseTool, PermissionClass, ToolContext, ToolResult, ToolStatus
from backend.tools.safety import (
    ToolSafetyError,
    display_argv,
    redact_secrets,
    resolve_tool_path,
    truncate_text,
)

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]


class ToolValidationError(ValueError):
    pass


class BaseLocalTool:
    name = ""
    description = ""
    permission_class = PermissionClass.READ_ONLY
    capabilities: list[str] = []
    input_schema: dict[str, Any] = {}
    enabled = True

    def __init__(self, policy: PolicyConfig, workspace_root: Path = WORKSPACE_ROOT) -> None:
        self._policy = policy
        self._workspace_root = workspace_root

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        return dict(raw)

    def classify(self, validated_input: dict[str, Any]) -> PermissionClass:
        return self.permission_class


class FilesystemListTool(BaseLocalTool):
    name = "filesystem.list"
    description = "List files under an allowed local path."
    permission_class = PermissionClass.READ_ONLY
    capabilities = ["filesystem", "read"]
    input_schema = {"type": "object", "properties": {"path": {"type": "string"}}}

    async def execute(
        self, context: ToolContext, validated_input: dict[str, Any], *, execution_id: str
    ) -> ToolResult:
        started = time.perf_counter()
        path = resolve_tool_path(
            self._workspace_root, self._policy, str(validated_input.get("path", "."))
        )
        if not path.exists():
            raise ToolSafetyError("Path does not exist.", code="PATH_NOT_FOUND")
        if not path.is_dir():
            raise ToolSafetyError("Path is not a directory.", code="PATH_NOT_DIRECTORY")
        entries = [
            {
                "name": child.name,
                "path": str(child.relative_to(self._workspace_root)),
                "kind": "directory" if child.is_dir() else "file",
                "size_bytes": child.stat().st_size if child.is_file() else None,
            }
            for child in sorted(
                path.iterdir(),
                key=lambda item: (not item.is_dir(), item.name.lower()),
            )
        ][:200]
        return result(
            execution_id, self.name, started, data={"entries": entries, "path": str(path)}
        )


class FilesystemReadTool(BaseLocalTool):
    name = "filesystem.read"
    description = "Read a UTF-8 compatible file from an allowed local path."
    permission_class = PermissionClass.READ_ONLY
    capabilities = ["filesystem", "read"]
    input_schema = {"type": "object", "properties": {"path": {"type": "string"}}}

    async def execute(
        self, context: ToolContext, validated_input: dict[str, Any], *, execution_id: str
    ) -> ToolResult:
        started = time.perf_counter()
        path = resolve_tool_path(
            self._workspace_root, self._policy, str(validated_input.get("path", ""))
        )
        if not path.is_file():
            raise ToolSafetyError("File does not exist.", code="FILE_NOT_FOUND")
        text = path.read_text(encoding="utf-8", errors="replace")
        text, truncated = truncate_text(
            redact_secrets(text),
            self._policy.command_execution.output_limit_bytes,
        )
        return result(
            execution_id,
            self.name,
            started,
            stdout=text,
            truncated=truncated,
            data={"path": str(path), "size_bytes": path.stat().st_size},
        )


class FilesystemSearchTool(BaseLocalTool):
    name = "filesystem.search"
    description = "Search text files under an allowed local path."
    permission_class = PermissionClass.READ_ONLY
    capabilities = ["filesystem", "read", "search"]
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "query": {"type": "string"}},
    }

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        query = str(raw.get("query", "")).strip()
        if not query:
            raise ToolValidationError("query is required")
        return {"path": str(raw.get("path", ".")), "query": query}

    async def execute(
        self, context: ToolContext, validated_input: dict[str, Any], *, execution_id: str
    ) -> ToolResult:
        started = time.perf_counter()
        root = resolve_tool_path(self._workspace_root, self._policy, validated_input["path"])
        paths = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        matches: list[dict[str, Any]] = []
        needle = str(validated_input["query"]).lower()
        for path in paths[:2000]:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if needle in line.lower():
                    matches.append(
                        {
                            "path": str(path.relative_to(self._workspace_root)),
                            "line": line_number,
                            "excerpt": redact_secrets(line.strip())[:500],
                        }
                    )
                    if len(matches) >= 100:
                        break
            if len(matches) >= 100:
                break
        return result(execution_id, self.name, started, data={"matches": matches})


class FilesystemWriteTool(BaseLocalTool):
    name = "filesystem.write"
    description = "Write a file atomically under an allowed local path."
    permission_class = PermissionClass.WRITE_LOCAL
    capabilities = ["filesystem", "write"]
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
    }

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        path = str(raw.get("path", "")).strip()
        if not path:
            raise ToolValidationError("path is required")
        return {"path": path, "content": str(raw.get("content", ""))}

    async def execute(
        self, context: ToolContext, validated_input: dict[str, Any], *, execution_id: str
    ) -> ToolResult:
        started = time.perf_counter()
        path = resolve_tool_path(self._workspace_root, self._policy, validated_input["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{path.name}.{execution_id}.tmp")
        temp.write_text(str(validated_input["content"]), encoding="utf-8")
        temp.replace(path)
        return result(
            execution_id,
            self.name,
            started,
            data={"path": str(path), "bytes_written": path.stat().st_size},
        )


class TerminalRunTool(BaseLocalTool):
    name = "terminal.run"
    description = "Run a local command using argv mode by default."
    permission_class = PermissionClass.READ_ONLY
    capabilities = ["terminal", "argv", "shell"]
    input_schema = {
        "type": "object",
        "properties": {
            "argv": {"type": "array", "items": {"type": "string"}},
            "cwd": {"type": "string"},
            "timeout_seconds": {"type": "integer"},
            "shell": {"type": "boolean"},
        },
    }

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        argv_raw = raw.get("argv")
        if not isinstance(argv_raw, list) or not argv_raw:
            raise ToolValidationError("argv must be a non-empty string array")
        argv = [str(item) for item in argv_raw]
        timeout = int(
            raw.get("timeout_seconds") or self._policy.command_execution.default_timeout_seconds
        )
        timeout = min(timeout, self._policy.command_execution.maximum_timeout_seconds)
        return {
            "argv": argv,
            "cwd": str(raw.get("cwd", ".")),
            "timeout_seconds": timeout,
            "shell": bool(raw.get("shell", False)),
        }

    def classify(self, validated_input: dict[str, Any]) -> PermissionClass:
        argv = [str(item).lower() for item in validated_input["argv"]]
        if validated_input.get("shell"):
            return PermissionClass.HIGH_IMPACT
        executable = Path(argv[0]).name
        high_impact_commands = {
            "del",
            "erase",
            "format",
            "powershell",
            "powershell.exe",
            "pwsh",
            "pwsh.exe",
            "rm",
            "rmdir",
            "shutdown",
            "taskkill",
        }
        write_commands = {
            "copy",
            "cp",
            "mkdir",
            "move",
            "mv",
            "new-item",
            "set-content",
        }
        if executable in high_impact_commands or any(
            token in argv for token in ("remove-item", "remove-item.exe")
        ):
            return PermissionClass.HIGH_IMPACT
        if executable in write_commands:
            return PermissionClass.WRITE_LOCAL
        return PermissionClass.READ_ONLY

    async def execute(
        self, context: ToolContext, validated_input: dict[str, Any], *, execution_id: str
    ) -> ToolResult:
        if validated_input.get("shell") and not self._policy.command_execution.shell_mode_enabled:
            raise ToolSafetyError("Shell mode is disabled by policy.", code="SHELL_DISABLED")
        cwd = resolve_tool_path(self._workspace_root, self._policy, validated_input["cwd"])
        argv = list(validated_input["argv"])
        return await run_subprocess(
            execution_id,
            self.name,
            argv,
            cwd,
            timeout_seconds=int(validated_input["timeout_seconds"]),
            output_limit=self._policy.command_execution.output_limit_bytes,
            shell=bool(validated_input.get("shell", False)),
        )


class GitTool(TerminalRunTool):
    def __init__(
        self,
        policy: PolicyConfig,
        name: str,
        description: str,
        command: list[str],
        permission: PermissionClass = PermissionClass.READ_ONLY,
        workspace_root: Path = WORKSPACE_ROOT,
    ) -> None:
        super().__init__(policy, workspace_root)
        self.name = name
        self.description = description
        self.permission_class = permission
        self._command = command
        self.capabilities = ["git", "read" if permission == PermissionClass.READ_ONLY else "write"]

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        cwd = str(raw.get("cwd", "."))
        timeout = int(
            raw.get("timeout_seconds") or self._policy.command_execution.default_timeout_seconds
        )
        return {"cwd": cwd, "timeout_seconds": timeout, "argv": ["git", *self._command]}

    def classify(self, validated_input: dict[str, Any]) -> PermissionClass:
        return self.permission_class


class GitBranchCreateTool(GitTool):
    def __init__(self, policy: PolicyConfig, workspace_root: Path = WORKSPACE_ROOT) -> None:
        super().__init__(
            policy,
            "git.branch_create",
            "Create a local Git branch after confirmation.",
            [],
            PermissionClass.WRITE_LOCAL,
            workspace_root,
        )

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        branch = str(raw.get("branch", "")).strip()
        if not branch:
            raise ToolValidationError("branch is required")
        return {
            "cwd": str(raw.get("cwd", ".")),
            "timeout_seconds": int(raw.get("timeout_seconds") or 15),
            "argv": ["git", "branch", branch],
        }


class PythonRunTool(TerminalRunTool):
    name = "python.run"
    description = "Run a Python snippet in a subprocess with timeout and output limits."
    permission_class = PermissionClass.WRITE_LOCAL
    capabilities = ["python", "subprocess"]
    input_schema = {"type": "object", "properties": {"code": {"type": "string"}}}

    def validate_input(self, raw: dict[str, Any]) -> dict[str, Any]:
        code = str(raw.get("code", ""))
        if not code.strip():
            raise ToolValidationError("code is required")
        timeout = int(
            raw.get("timeout_seconds") or self._policy.command_execution.default_timeout_seconds
        )
        timeout = min(timeout, self._policy.command_execution.maximum_timeout_seconds)
        return {
            "argv": ["python", "-c", code],
            "cwd": str(raw.get("cwd", ".")),
            "timeout_seconds": timeout,
            "shell": False,
        }

    def classify(self, validated_input: dict[str, Any]) -> PermissionClass:
        return PermissionClass.WRITE_LOCAL


async def run_subprocess(
    execution_id: str,
    tool_name: str,
    argv: list[str],
    cwd: Path,
    *,
    timeout_seconds: int,
    output_limit: int,
    shell: bool = False,
) -> ToolResult:
    started = time.perf_counter()
    started_at = utc_now()
    if shell:
        command = display_argv(argv)
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    else:
        executable = shutil.which(argv[0]) or argv[0]
        process = await asyncio.create_subprocess_exec(
            executable,
            *argv[1:],
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    stdout_task = asyncio.create_task(read_limited_stream(process.stdout, output_limit))
    stderr_task = asyncio.create_task(read_limited_stream(process.stderr, output_limit))
    timed_out = False
    try:
        await asyncio.wait_for(process.wait(), timeout=timeout_seconds)
    except TimeoutError:
        timed_out = True
        await terminate_process_tree(process)
        await process.wait()
    stdout_capture, stderr_capture = await asyncio.gather(stdout_task, stderr_task)
    stdout_bytes, stdout_capture_truncated = stdout_capture
    stderr_bytes, stderr_capture_truncated = stderr_capture
    stdout_text, stdout_truncated = truncate_text(
        redact_secrets(stdout_bytes.decode("utf-8", errors="replace")),
        output_limit,
    )
    stderr_text, stderr_truncated = truncate_text(
        redact_secrets(stderr_bytes.decode("utf-8", errors="replace")),
        output_limit,
    )
    if stdout_capture_truncated and not stdout_truncated:
        stdout_text = f"{stdout_text}\n[output truncated]"
        stdout_truncated = True
    if stderr_capture_truncated and not stderr_truncated:
        stderr_text = f"{stderr_text}\n[output truncated]"
        stderr_truncated = True
    return ToolResult(
        execution_id=execution_id,
        tool=tool_name,
        status=ToolStatus.TIMED_OUT
        if timed_out
        else (ToolStatus.COMPLETED if process.returncode == 0 else ToolStatus.FAILED),
        started_at=started_at,
        completed_at=utc_now(),
        duration_ms=round((time.perf_counter() - started) * 1000, 3),
        exit_code=process.returncode,
        stdout=stdout_text,
        stderr=stderr_text,
        truncated=stdout_truncated or stderr_truncated,
        error_code=(
            "TOOL_TIMEOUT" if timed_out else (None if process.returncode == 0 else "NONZERO_EXIT")
        ),
        error_message="Tool execution timed out." if timed_out else None,
        data={"cwd": str(cwd), "command": display_argv(argv), "shell": shell},
    )


async def read_limited_stream(
    stream: asyncio.StreamReader | None, limit_bytes: int
) -> tuple[bytes, bool]:
    if stream is None:
        return b"", False
    chunks = bytearray()
    truncated = False
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        remaining = limit_bytes - len(chunks)
        if remaining > 0:
            chunks.extend(chunk[:remaining])
        if len(chunk) > remaining:
            truncated = True
    return bytes(chunks), truncated


async def terminate_process_tree(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    if os.name == "nt" and process.pid:
        killer = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await killer.communicate()
    else:
        process.kill()


def result(
    execution_id: str,
    tool_name: str,
    started: float,
    *,
    stdout: str | None = None,
    data: dict[str, Any] | None = None,
    truncated: bool = False,
) -> ToolResult:
    return ToolResult(
        execution_id=execution_id,
        tool=tool_name,
        status=ToolStatus.COMPLETED,
        started_at=utc_now(),
        completed_at=utc_now(),
        duration_ms=round((time.perf_counter() - started) * 1000, 3),
        stdout=stdout,
        data=data or {},
        truncated=truncated,
    )


def build_builtin_tools(
    policy: PolicyConfig, workspace_root: Path = WORKSPACE_ROOT
) -> list[BaseTool]:
    return [
        FilesystemListTool(policy, workspace_root),
        FilesystemReadTool(policy, workspace_root),
        FilesystemSearchTool(policy, workspace_root),
        FilesystemWriteTool(policy, workspace_root),
        TerminalRunTool(policy, workspace_root),
        GitTool(
            policy,
            "git.status",
            "Show Git working tree status.",
            ["status", "--short"],
            workspace_root=workspace_root,
        ),
        GitTool(
            policy,
            "git.diff",
            "Show Git diff.",
            ["diff", "--"],
            workspace_root=workspace_root,
        ),
        GitTool(
            policy,
            "git.log",
            "Show recent Git commits.",
            ["log", "--oneline", "-n", "20"],
            workspace_root=workspace_root,
        ),
        GitTool(
            policy,
            "git.branches",
            "List local Git branches.",
            ["branch", "--list"],
            workspace_root=workspace_root,
        ),
        GitBranchCreateTool(policy, workspace_root),
        PythonRunTool(policy, workspace_root),
    ]
