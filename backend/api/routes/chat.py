"""Streaming chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette import status

from backend.api.errors import ApplicationError
from backend.api.schemas.conversation import ChatStreamRequest
from backend.services.chat import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(request: Request, body: ChatStreamRequest) -> StreamingResponse:
    service: ChatService = request.app.state.chat_service
    request_id = getattr(request.state, "request_id", "unknown")
    return StreamingResponse(
        service.stream(body, request_id=request_id, is_disconnected=request.is_disconnected),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generations/{generation_id}/cancel")
async def cancel_generation(request: Request, generation_id: str) -> dict[str, bool]:
    service: ChatService = request.app.state.chat_service
    cancelled = await service.cancel(generation_id)
    if not cancelled:
        raise ApplicationError(
            "GENERATION_NOT_ACTIVE",
            "Generation is not active.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return {"cancelled": True}
