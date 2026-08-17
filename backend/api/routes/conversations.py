"""Persistent conversation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from backend.api.dependencies.core import get_db_session
from backend.api.schemas.conversation import (
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationPatchRequest,
    ConversationRead,
    MessageListResponse,
)
from backend.services.conversations import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])
DBSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreateRequest,
    session: DBSession,
) -> ConversationRead:
    return await ConversationService(session).create(body)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    session: DBSession,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    archived: bool | None = Query(default=False),
    search: str | None = Query(default=None, max_length=120),
) -> ConversationListResponse:
    return await ConversationService(session).list(
        limit=limit,
        offset=offset,
        archived=archived,
        search=search,
    )


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: str,
    session: DBSession,
) -> ConversationRead:
    return await ConversationService(session).get(conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def patch_conversation(
    conversation_id: str,
    body: ConversationPatchRequest,
    session: DBSession,
) -> ConversationRead:
    return await ConversationService(session).patch(conversation_id, body)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    session: DBSession,
) -> Response:
    await ConversationService(session).delete(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
async def list_messages(
    conversation_id: str,
    session: DBSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> MessageListResponse:
    return await ConversationService(session).messages(
        conversation_id,
        limit=limit,
        offset=offset,
    )
