"""In-memory active generation tracking.

Active cancellation state is runtime-only and does not survive process restarts. Durable message
state is stored in the database.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


class GenerationConflictError(Exception):
    pass


@dataclass(slots=True)
class ActiveGeneration:
    generation_id: str
    conversation_id: str
    cancel_event: asyncio.Event


class GenerationManager:
    def __init__(self) -> None:
        self._active: dict[str, ActiveGeneration] = {}
        self._conversation_index: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def register(self, generation_id: str, conversation_id: str) -> ActiveGeneration:
        async with self._lock:
            if conversation_id in self._conversation_index:
                raise GenerationConflictError("Conversation already has an active generation.")
            active = ActiveGeneration(
                generation_id=generation_id,
                conversation_id=conversation_id,
                cancel_event=asyncio.Event(),
            )
            self._active[generation_id] = active
            self._conversation_index[conversation_id] = generation_id
            return active

    async def cancel(self, generation_id: str) -> bool:
        async with self._lock:
            active = self._active.get(generation_id)
            if active is None:
                return False
            active.cancel_event.set()
            return True

    async def cleanup(self, generation_id: str) -> None:
        async with self._lock:
            active = self._active.pop(generation_id, None)
            if active is not None:
                self._conversation_index.pop(active.conversation_id, None)

    def is_cancelled(self, generation_id: str) -> bool:
        active = self._active.get(generation_id)
        return active.cancel_event.is_set() if active is not None else False

    def active_count(self) -> int:
        return len(self._active)
