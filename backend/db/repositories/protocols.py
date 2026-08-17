"""Repository protocol definitions."""

from __future__ import annotations

from typing import Any, Protocol

from backend.db.models import Conversation, Message, Setting, User


class UserRepository(Protocol):
    async def create(self, display_name: str) -> User: ...
    async def get(self, user_id: str) -> User | None: ...
    async def get_or_create_local(self) -> User: ...


class ConversationRepository(Protocol):
    async def create(self, user_id: str, title: str) -> Conversation: ...
    async def get(self, conversation_id: str) -> Conversation | None: ...
    async def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None: ...
    async def list_for_user(
        self,
        user_id: str,
        *,
        limit: int,
        offset: int,
        archived: bool | None = False,
        search: str | None = None,
    ) -> tuple[list[Conversation], int]: ...
    async def rename(self, conversation: Conversation, title: str) -> Conversation: ...
    async def set_archived(self, conversation: Conversation, archived: bool) -> Conversation: ...
    async def touch(self, conversation: Conversation) -> Conversation: ...
    async def delete(self, conversation: Conversation) -> None: ...


class MessageRepository(Protocol):
    async def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message: ...
    async def get(self, message_id: str) -> Message | None: ...
    async def get_by_client_request_id(self, client_request_id: str) -> Message | None: ...
    async def get_by_generation_id(self, generation_id: str) -> Message | None: ...
    async def list_for_conversation(
        self,
        conversation_id: str,
        *,
        limit: int,
        offset: int,
        ascending: bool = True,
    ) -> tuple[list[Message], int]: ...
    async def recent_for_context(self, conversation_id: str, limit: int) -> list[Message]: ...
    async def update_generation(
        self,
        message: Message,
        *,
        content: str | None = None,
        status: str | None = None,
        finish_reason: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        time_to_first_token_ms: float | None = None,
        duration_ms: float | None = None,
        tokens_per_second: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message: ...
    async def mark_incomplete_generations_interrupted(self) -> int: ...


class SettingRepository(Protocol):
    async def set(self, key: str, value: dict[str, Any]) -> Setting: ...
    async def get(self, key: str) -> Setting | None: ...
