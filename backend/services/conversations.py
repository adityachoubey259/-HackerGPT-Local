"""Persistent conversation application service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.errors import ApplicationError
from backend.api.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationPatchRequest,
    ConversationRead,
    MessageListResponse,
    MessageRead,
    Pagination,
)
from backend.db.models import Conversation, Message
from backend.db.repositories.sqlalchemy import (
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageRepository,
    SqlAlchemyUserRepository,
)


class ConversationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = SqlAlchemyUserRepository(session)
        self._conversations = SqlAlchemyConversationRepository(session)
        self._messages = SqlAlchemyMessageRepository(session)

    async def create(self, request: ConversationCreateRequest) -> ConversationRead:
        user = await self._users.get_or_create_local()
        title = request.title or "Untitled conversation"
        conversation = await self._conversations.create(user.id, title)
        return conversation_to_read(conversation)

    async def list(
        self,
        *,
        limit: int,
        offset: int,
        archived: bool | None,
        search: str | None,
    ) -> ConversationListResponse:
        user = await self._users.get_or_create_local()
        items, total = await self._conversations.list_for_user(
            user.id,
            limit=limit,
            offset=offset,
            archived=archived,
            search=" ".join(search.split()) if search else None,
        )
        return ConversationListResponse(
            items=[conversation_to_read(item) for item in items],
            pagination=Pagination(limit=limit, offset=offset, total=total),
        )

    async def get(self, conversation_id: str) -> ConversationRead:
        return conversation_to_read(await self._get_scoped(conversation_id))

    async def patch(
        self,
        conversation_id: str,
        request: ConversationPatchRequest,
    ) -> ConversationRead:
        conversation = await self._get_scoped(conversation_id)
        if request.title is not None:
            conversation = await self._conversations.rename(conversation, request.title)
        if request.archived is not None:
            conversation = await self._conversations.set_archived(conversation, request.archived)
        if request.agent_id is not None:
            conversation = await self._conversations.set_agent(conversation, request.agent_id)
        return conversation_to_read(conversation)

    async def delete(self, conversation_id: str) -> None:
        conversation = await self._get_scoped(conversation_id)
        await self._conversations.delete(conversation)

    async def messages(
        self,
        conversation_id: str,
        *,
        limit: int,
        offset: int,
    ) -> MessageListResponse:
        conversation = await self._get_scoped(conversation_id)
        messages, total = await self._messages.list_for_conversation(
            conversation.id,
            limit=limit,
            offset=offset,
            ascending=True,
        )
        return MessageListResponse(
            items=[message_to_read(message) for message in messages],
            pagination=Pagination(limit=limit, offset=offset, total=total),
        )

    async def _get_scoped(self, conversation_id: str) -> Conversation:
        user = await self._users.get_or_create_local()
        conversation = await self._conversations.get_for_user(conversation_id, user.id)
        if conversation is None:
            raise ApplicationError(
                "CONVERSATION_NOT_FOUND",
                "Conversation was not found.",
                status_code=404,
            )
        return conversation


def conversation_to_read(conversation: Conversation) -> ConversationRead:
    return ConversationRead(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        agent_id=conversation.agent_id,
        archived=conversation.archived,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def message_to_read(message: Message) -> MessageRead:
    return MessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        metadata=message.metadata_json,
        client_request_id=message.client_request_id,
        generation_id=message.generation_id,
        generation_status=message.generation_status,
        provider=message.provider,
        model=message.model,
        finish_reason=message.finish_reason,
        prompt_tokens=message.prompt_tokens,
        completion_tokens=message.completion_tokens,
        total_tokens=message.total_tokens,
        time_to_first_token_ms=message.time_to_first_token_ms,
        duration_ms=message.duration_ms,
        tokens_per_second=message.tokens_per_second,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )
