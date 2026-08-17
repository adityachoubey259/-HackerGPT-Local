"""Secure tool execution service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api.errors import ApplicationError
from backend.api.schemas.tools import (
    ToolConfirmationRead,
    ToolExecuteResponse,
    ToolExecutionListResponse,
    ToolExecutionRead,
)
from backend.core.policy import PolicyConfig
from backend.core.time import utc_now
from backend.db.models import ToolConfirmation, ToolExecution
from backend.db.repositories.sqlalchemy import SqlAlchemyToolRepository, SqlAlchemyUserRepository
from backend.services.agents import AgentService
from backend.tools.models import (
    BaseTool,
    PermissionClass,
    PermissionDecisionType,
    ToolContext,
    ToolDefinition,
    ToolResult,
    ToolStatus,
)
from backend.tools.permissions import PermissionService
from backend.tools.registry import ToolRegistry, ToolRegistryError
from backend.tools.safety import ToolSafetyError, display_argv, stable_hash


class ToolService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        policy: PolicyConfig,
        registry: ToolRegistry,
        agent_service: AgentService,
        *,
        workspace_root: Path,
    ) -> None:
        self._session_factory = session_factory
        self._policy = policy
        self._registry = registry
        self._agent_service = agent_service
        self._permissions = PermissionService(policy)
        self._workspace_root = workspace_root

    def list_tools(self) -> list[ToolDefinition]:
        return self._registry.list(include_disabled=True)

    async def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, object],
        agent_id: str | None,
        conversation_id: str | None,
        request_id: str | None = None,
        generation_id: str | None = None,
    ) -> ToolExecuteResponse:
        user_id = await self._local_user_id()
        agent = await self._agent_service.resolve(agent_id)
        tool = self._get_tool(tool_name)
        validated = self._validate(tool, arguments)
        classified = tool.classify(validated)
        definition = next(
            item for item in self._registry.list(include_disabled=True) if item.name == tool.name
        )
        decision = self._permissions.evaluate(
            tool=definition, classified_permission=classified, agent=agent
        )
        payload = {
            "tool_name": tool.name,
            "arguments": validated,
            "agent_id": agent.id,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "generation_id": generation_id,
        }
        payload_hash = stable_hash(payload)
        command_display = command_for(tool.name, validated)
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            execution = await repo.create_execution(
                user_id=user_id,
                conversation_id=conversation_id,
                agent_id=agent.id,
                request_id=request_id,
                generation_id=generation_id,
                tool_name=tool.name,
                permission_class=classified.value,
                status=status_for_decision(decision.decision).value,
                input_payload=validated,
                input_hash=payload_hash,
                working_directory=str(self._workspace_root),
                command_display=command_display,
            )
            confirmation: ToolConfirmation | None = None
            if decision.decision == PermissionDecisionType.REQUIRE_CONFIRMATION:
                confirmation = await repo.create_confirmation(
                    execution_id=execution.id,
                    user_id=user_id,
                    tool_name=tool.name,
                    permission_class=classified.value,
                    payload_hash=payload_hash,
                    payload=payload,
                    risk_summary=decision.risk_summary,
                    expires_at=utc_now()
                    + timedelta(seconds=self._policy.command_execution.confirmation_ttl_seconds),
                )
            await session.commit()
        if decision.decision == PermissionDecisionType.DENY:
            return ToolExecuteResponse(
                execution=execution_to_read(execution),
                confirmation=None,
                decision=decision.decision.value,
                reason=decision.reason,
            )
        if confirmation is not None:
            return ToolExecuteResponse(
                execution=execution_to_read(execution),
                confirmation=confirmation_to_read(confirmation),
                decision=decision.decision.value,
                reason=decision.reason,
            )
        executed = await self._execute_stored(execution.id, user_id)
        return ToolExecuteResponse(
            execution=execution_to_read(executed),
            confirmation=None,
            decision=decision.decision.value,
            reason=decision.reason,
        )

    async def approve(self, confirmation_id: str) -> tuple[ToolExecution, ToolConfirmation]:
        user_id = await self._local_user_id()
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            confirmation = await repo.get_confirmation(user_id, confirmation_id)
            if confirmation is None:
                raise not_found("CONFIRMATION_NOT_FOUND", "Confirmation not found.")
            if confirmation.status != "pending":
                raise conflict("CONFIRMATION_NOT_PENDING", "Confirmation is not pending.")
            if utc_aware(confirmation.expires_at) <= utc_now():
                await repo.update_confirmation(confirmation, status="expired")
                await session.commit()
                raise conflict("CONFIRMATION_EXPIRED", "Confirmation expired.")
            execution = await repo.get_execution(user_id, confirmation.execution_id)
            if execution is None:
                raise not_found("TOOL_EXECUTION_NOT_FOUND", "Execution not found.")
            expected_payload = payload_for_execution(execution)
            if (
                execution.input_hash != confirmation.payload_hash
                or stable_hash(confirmation.payload) != confirmation.payload_hash
                or stable_hash(expected_payload) != confirmation.payload_hash
            ):
                raise conflict(
                    "CONFIRMATION_TAMPERED",
                    "Stored confirmation payload does not match.",
                )
            await repo.update_confirmation(confirmation, status="approved", decided_at=utc_now())
            await session.commit()
        executed = await self._execute_stored(execution.id, user_id)
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            refreshed = await repo.get_confirmation(user_id, confirmation_id)
        if refreshed is None:
            raise not_found("CONFIRMATION_NOT_FOUND", "Confirmation not found.")
        return executed, refreshed

    async def deny(self, confirmation_id: str) -> tuple[ToolExecution, ToolConfirmation]:
        user_id = await self._local_user_id()
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            confirmation = await repo.get_confirmation(user_id, confirmation_id)
            if confirmation is None:
                raise not_found("CONFIRMATION_NOT_FOUND", "Confirmation not found.")
            execution = await repo.get_execution(user_id, confirmation.execution_id)
            if execution is None:
                raise not_found("TOOL_EXECUTION_NOT_FOUND", "Execution not found.")
            await repo.update_confirmation(confirmation, status="denied", decided_at=utc_now())
            await repo.update_execution(execution, status=ToolStatus.CANCELLED.value)
            await session.commit()
        return execution, confirmation

    async def cancel(self, execution_id: str) -> ToolExecution:
        user_id = await self._local_user_id()
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            execution = await repo.get_execution(user_id, execution_id)
            if execution is None:
                raise not_found("TOOL_EXECUTION_NOT_FOUND", "Execution not found.")
            await repo.update_execution(execution, status=ToolStatus.CANCELLED.value)
            await session.commit()
        return execution

    async def history(self, *, limit: int, offset: int) -> ToolExecutionListResponse:
        user_id = await self._local_user_id()
        async with self._session_factory() as session:
            items, total = await SqlAlchemyToolRepository(session).list_executions(
                user_id, limit=limit, offset=offset
            )
        return ToolExecutionListResponse(
            items=[execution_to_read(item) for item in items],
            total=total,
        )

    async def pending_confirmations(self) -> list[ToolConfirmationRead]:
        user_id = await self._local_user_id()
        async with self._session_factory() as session:
            items = await SqlAlchemyToolRepository(session).list_confirmations(user_id)
        return [confirmation_to_read(item) for item in items]

    async def _execute_stored(self, execution_id: str, user_id: str) -> ToolExecution:
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            execution = await repo.get_execution(user_id, execution_id)
            if execution is None:
                raise not_found("TOOL_EXECUTION_NOT_FOUND", "Execution not found.")
            if execution.status == ToolStatus.CANCELLED.value:
                return execution
            await repo.update_execution(
                execution,
                status=ToolStatus.RUNNING.value,
                started_at=utc_now(),
            )
            await session.commit()
        tool = self._get_tool(execution.tool_name)
        context = ToolContext(
            user_id=user_id,
            conversation_id=execution.conversation_id,
            agent_id=execution.agent_id,
            request_id=execution.request_id,
            generation_id=execution.generation_id,
            working_directory=str(self._workspace_root),
            policy_snapshot=self._policy.model_dump(mode="json"),
        )
        result: ToolResult | None
        error_code: str | None
        error_message: str | None
        try:
            result = await tool.execute(context, execution.input, execution_id=execution.id)
        except (ToolSafetyError, ValueError) as exc:
            result = None
            error_code = getattr(exc, "code", "TOOL_ERROR")
            error_message = str(exc)
        else:
            error_code = result.error_code if result is not None else None
            error_message = result.error_message if result is not None else None
        async with self._session_factory() as session:
            repo = SqlAlchemyToolRepository(session)
            stored = await repo.get_execution(user_id, execution_id)
            if stored is None:
                raise not_found("TOOL_EXECUTION_NOT_FOUND", "Execution not found.")
            await repo.update_execution(
                stored,
                status=(result.status.value if result else ToolStatus.FAILED.value),
                stdout=result.stdout if result else None,
                stderr=result.stderr if result else None,
                exit_code=result.exit_code if result else None,
                data=result.data if result else {},
                error_code=error_code,
                error_message=error_message,
                truncated=result.truncated if result else False,
                duration_ms=result.duration_ms if result else None,
                completed_at=utc_now(),
            )
            await session.commit()
            return stored

    async def _local_user_id(self) -> str:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            await session.commit()
            return user.id

    def _get_tool(self, name: str) -> BaseTool:
        try:
            return self._registry.get(name)
        except ToolRegistryError as exc:
            raise ApplicationError("TOOL_NOT_FOUND", str(exc), status_code=404) from exc

    @staticmethod
    def _validate(tool: BaseTool, arguments: dict[str, object]) -> dict[str, object]:
        try:
            return tool.validate_input(arguments)
        except ValueError as exc:
            raise ApplicationError("TOOL_INPUT_INVALID", str(exc), status_code=422) from exc


def status_for_decision(decision: PermissionDecisionType) -> ToolStatus:
    if decision == PermissionDecisionType.ALLOW:
        return ToolStatus.REQUESTED
    if decision == PermissionDecisionType.REQUIRE_CONFIRMATION:
        return ToolStatus.PENDING_CONFIRMATION
    return ToolStatus.DENIED


def command_for(tool_name: str, arguments: dict[str, object]) -> str | None:
    argv = arguments.get("argv")
    if isinstance(argv, list):
        return display_argv([str(part) for part in argv])
    if tool_name == "filesystem.write":
        return f"write {arguments.get('path')}"
    return None


def payload_for_execution(execution: ToolExecution) -> dict[str, object]:
    return {
        "tool_name": execution.tool_name,
        "arguments": execution.input,
        "agent_id": execution.agent_id,
        "conversation_id": execution.conversation_id,
        "request_id": execution.request_id,
        "generation_id": execution.generation_id,
    }


def utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def execution_to_read(row: ToolExecution) -> ToolExecutionRead:
    return ToolExecutionRead(
        id=row.id,
        tool_name=row.tool_name,
        permission_class=PermissionClass(row.permission_class),
        status=ToolStatus(row.status),
        input=row.input,
        working_directory=row.working_directory,
        command_display=row.command_display,
        stdout=row.stdout,
        stderr=row.stderr,
        exit_code=row.exit_code,
        data=row.data,
        error_code=row.error_code,
        error_message=row.error_message,
        truncated=row.truncated,
        duration_ms=row.duration_ms,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def confirmation_to_read(row: ToolConfirmation) -> ToolConfirmationRead:
    return ToolConfirmationRead(
        id=row.id,
        execution_id=row.execution_id,
        tool_name=row.tool_name,
        permission_class=PermissionClass(row.permission_class),
        status=row.status,
        risk_summary=row.risk_summary,
        expires_at=row.expires_at,
        created_at=row.created_at,
    )


def not_found(code: str, message: str) -> ApplicationError:
    return ApplicationError(code, message, status_code=404)


def conflict(code: str, message: str) -> ApplicationError:
    return ApplicationError(code, message, status_code=409)
