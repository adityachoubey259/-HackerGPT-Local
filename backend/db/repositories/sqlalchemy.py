"""SQLAlchemy repository implementations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.time import utc_now
from backend.db.models import (
    Conversation,
    CustomAgent,
    Document,
    DocumentChunk,
    EmbeddingCache,
    IngestionJob,
    Memory,
    MemoryEvent,
    Message,
    MessageRetrieval,
    ResearchCacheEntry,
    ResearchSession,
    ResearchSource,
    SecurityFinding,
    SecurityNote,
    SecurityScope,
    SecurityWorkspace,
    Setting,
    ToolConfirmation,
    ToolExecution,
    User,
)
from backend.rag.models import DocumentChunkDraft

LOCAL_USER_ID = "local-user"


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, display_name: str) -> User:
        user = User(display_name=display_name)
        self._session.add(user)
        await self._session.flush()
        return user

    async def get(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def get_or_create_local(self) -> User:
        existing = await self.get(LOCAL_USER_ID)
        if existing is not None:
            return existing
        user = User(id=LOCAL_USER_ID, display_name="Local User")
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def set_auth_fields(
        self,
        user: User,
        *,
        username: str,
        password_hash: str,
        role: str,
        is_bootstrap: bool,
        auth_metadata: dict[str, Any],
    ) -> User:
        user.username = username
        user.password_hash = password_hash
        user.role = role
        user.is_bootstrap = is_bootstrap
        user.auth_metadata = auth_metadata
        user.updated_at = utc_now()
        await self._session.flush()
        return user

    async def record_login(self, user: User, timestamp: str) -> User:
        user.auth_metadata = user.auth_metadata | {"last_login_at": timestamp}
        user.updated_at = utc_now()
        await self._session.flush()
        return user

    async def update_password_hash(
        self,
        user: User,
        password_hash: str,
        metadata: dict[str, Any],
    ) -> User:
        user.password_hash = password_hash
        user.auth_metadata = metadata
        user.updated_at = utc_now()
        await self._session.flush()
        return user


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: str, title: str, agent_id: str | None = None) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title, agent_id=agent_id)
        self._session.add(conversation)
        await self._session.flush()
        return conversation

    async def get(self, conversation_id: str) -> Conversation | None:
        return await self._session.get(Conversation, conversation_id)

    async def get_for_user(self, conversation_id: str, user_id: str) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        *,
        limit: int,
        offset: int,
        archived: bool | None = False,
        search: str | None = None,
    ) -> tuple[list[Conversation], int]:
        conditions = [Conversation.user_id == user_id]
        if archived is not None:
            conditions.append(Conversation.archived.is_(archived))
        if search:
            pattern = f"%{search}%"
            conditions.append(Conversation.title.ilike(pattern))
        count_result = await self._session.execute(
            select(func.count()).select_from(Conversation).where(*conditions)
        )
        total = int(count_result.scalar_one())
        result = await self._session.execute(
            select(Conversation)
            .where(*conditions)
            .order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def rename(self, conversation: Conversation, title: str) -> Conversation:
        conversation.title = title
        conversation.updated_at = utc_now()
        await self._session.flush()
        return conversation

    async def set_archived(self, conversation: Conversation, archived: bool) -> Conversation:
        conversation.archived = archived
        conversation.updated_at = utc_now()
        await self._session.flush()
        return conversation

    async def touch(self, conversation: Conversation) -> Conversation:
        conversation.updated_at = utc_now()
        await self._session.flush()
        return conversation

    async def set_agent(self, conversation: Conversation, agent_id: str | None) -> Conversation:
        conversation.agent_id = agent_id
        conversation.updated_at = utc_now()
        await self._session.flush()
        return conversation

    async def delete(self, conversation: Conversation) -> None:
        await self._session.delete(conversation)
        await self._session.flush()


class SqlAlchemyMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=metadata or {},
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def create_user_message(
        self,
        conversation_id: str,
        content: str,
        client_request_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
            client_request_id=client_request_id,
            metadata_json=metadata or {},
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def create_assistant_generation(
        self,
        conversation_id: str,
        *,
        generation_id: str,
        provider: str,
        model: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content="",
            generation_id=generation_id,
            provider=provider,
            model=model,
            generation_status=status,
            metadata_json=metadata or {},
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def get(self, message_id: str) -> Message | None:
        return await self._session.get(Message, message_id)

    async def get_by_client_request_id(self, client_request_id: str) -> Message | None:
        result = await self._session.execute(
            select(Message).where(Message.client_request_id == client_request_id)
        )
        return result.scalar_one_or_none()

    async def get_by_generation_id(self, generation_id: str) -> Message | None:
        result = await self._session.execute(
            select(Message).where(Message.generation_id == generation_id)
        )
        return result.scalar_one_or_none()

    async def list_for_conversation(
        self,
        conversation_id: str,
        *,
        limit: int,
        offset: int,
        ascending: bool = True,
    ) -> tuple[list[Message], int]:
        count_result = await self._session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        total = int(count_result.scalar_one())
        order = Message.created_at.asc() if ascending else Message.created_at.desc()
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(order)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def recent_for_context(self, conversation_id: str, limit: int) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def search_conversation_messages(
        self,
        conversation_ids: list[str],
        search: str,
    ) -> set[str]:
        if not conversation_ids:
            return set()
        pattern = f"%{search}%"
        result = await self._session.execute(
            select(Message.conversation_id)
            .where(Message.conversation_id.in_(conversation_ids))
            .where(or_(Message.content.ilike(pattern), Message.metadata_json.is_not(None)))
        )
        return {row[0] for row in result.all()}

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
    ) -> Message:
        if content is not None:
            message.content = content
        if status is not None:
            message.generation_status = status
        if finish_reason is not None:
            message.finish_reason = finish_reason
        if prompt_tokens is not None:
            message.prompt_tokens = prompt_tokens
        if completion_tokens is not None:
            message.completion_tokens = completion_tokens
        if total_tokens is not None:
            message.total_tokens = total_tokens
        if time_to_first_token_ms is not None:
            message.time_to_first_token_ms = time_to_first_token_ms
        if duration_ms is not None:
            message.duration_ms = duration_ms
        if tokens_per_second is not None:
            message.tokens_per_second = tokens_per_second
        if metadata is not None:
            message.metadata_json = metadata
        message.updated_at = utc_now()
        await self._session.flush()
        return message

    async def mark_incomplete_generations_interrupted(self) -> int:
        result = await self._session.execute(
            select(Message).where(Message.generation_status.in_(["pending", "streaming"]))
        )
        messages = list(result.scalars().all())
        for message in messages:
            message.generation_status = "interrupted"
            message.finish_reason = "backend_restart"
            message.updated_at = utc_now()
        await self._session.flush()
        return len(messages)

    async def delete_for_conversation(self, conversation_id: str) -> None:
        await self._session.execute(
            delete(Message).where(Message.conversation_id == conversation_id)
        )
        await self._session.flush()


class SqlAlchemySettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set(self, key: str, value: dict[str, Any]) -> Setting:
        existing = await self.get(key)
        if existing is not None:
            existing.value = value
            await self._session.flush()
            return existing
        setting = Setting(key=key, value=value)
        self._session.add(setting)
        await self._session.flush()
        return setting

    async def get(self, key: str) -> Setting | None:
        result = await self._session.execute(select(Setting).where(Setting.key == key))
        return result.scalar_one_or_none()


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_document(
        self,
        *,
        user_id: str,
        name: str,
        source: str,
        source_path: str | None,
        mime_type: str | None,
        size_bytes: int,
        checksum: str,
        status: str,
        parser: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        document = Document(
            user_id=user_id,
            name=name,
            source=source,
            source_path=source_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=checksum,
            status=status,
            parser=parser,
            title=title,
            tags=tags or [],
            metadata_json=metadata or {},
        )
        self._session.add(document)
        await self._session.flush()
        return document

    async def get_document(self, document_id: str, user_id: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_documents_by_ids(self, document_ids: list[str]) -> list[Document]:
        if not document_ids:
            return []
        result = await self._session.execute(select(Document).where(Document.id.in_(document_ids)))
        return list(result.scalars().all())

    async def list_documents(
        self,
        user_id: str,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        conditions = [Document.user_id == user_id]
        if status:
            conditions.append(Document.status == status)
        if search:
            pattern = f"%{search}%"
            conditions.append(or_(Document.name.ilike(pattern), Document.title.ilike(pattern)))
        count_result = await self._session.execute(
            select(func.count()).select_from(Document).where(*conditions)
        )
        result = await self._session.execute(
            select(Document)
            .where(*conditions)
            .order_by(Document.updated_at.desc(), Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(count_result.scalar_one())

    async def update_document(
        self,
        document: Document,
        *,
        status: str | None = None,
        parser: str | None = None,
        title: str | None = None,
        indexed_at: datetime | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        if status is not None:
            document.status = status
        if parser is not None:
            document.parser = parser
        if title is not None:
            document.title = title
        if indexed_at is not None:
            document.indexed_at = indexed_at
        if failure_code is not None:
            document.failure_code = failure_code
        if failure_message is not None:
            document.failure_message = failure_message
        if metadata is not None:
            document.metadata_json = metadata
        document.updated_at = utc_now()
        await self._session.flush()
        return document

    async def delete_document(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.flush()

    async def replace_chunks(
        self,
        document: Document,
        chunks: list[DocumentChunkDraft],
        *,
        embedding_provider: str,
        embedding_model: str,
        embedding_dimension: int,
    ) -> list[DocumentChunk]:
        await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        created: list[DocumentChunk] = []
        for chunk in chunks:
            row = DocumentChunk(
                document_id=document.id,
                user_id=document.user_id,
                chunk_index=chunk.chunk_index,
                citation_id=f"D{document.id[:8]}-{chunk.chunk_index + 1}",
                text=chunk.text,
                page_number=chunk.page_number,
                section=chunk.section,
                source_path=chunk.source_path,
                checksum=chunk.checksum,
                token_count=chunk.token_count,
                character_count=chunk.character_count,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model,
                embedding_dimension=embedding_dimension,
                tags=chunk.tags,
                metadata_json=chunk.metadata,
            )
            self._session.add(row)
            created.append(row)
        await self._session.flush()
        return created

    async def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []
        result = await self._session.execute(
            select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
        )
        return list(result.scalars().all())

    async def list_chunks(self, document_id: str) -> list[DocumentChunk]:
        result = await self._session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def stats(self, user_id: str) -> tuple[int, int]:
        document_count = await self._session.scalar(
            select(func.count()).select_from(Document).where(Document.user_id == user_id)
        )
        chunk_count = await self._session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.user_id == user_id)
        )
        return int(document_count or 0), int(chunk_count or 0)

    async def create_job(
        self,
        *,
        user_id: str,
        source: str,
        document_id: str | None = None,
        total_files: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionJob:
        job = IngestionJob(
            user_id=user_id,
            document_id=document_id,
            source=source,
            status="queued",
            total_files=total_files,
            metadata_json=metadata or {},
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def update_job(
        self,
        job: IngestionJob,
        *,
        status: str,
        processed_files: int | None = None,
        chunks_indexed: int | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
    ) -> IngestionJob:
        job.status = status
        if processed_files is not None:
            job.processed_files = processed_files
        if chunks_indexed is not None:
            job.chunks_indexed = chunks_indexed
        if failure_code is not None:
            job.failure_code = failure_code
        if failure_message is not None:
            job.failure_message = failure_message
        job.updated_at = utc_now()
        await self._session.flush()
        return job

    async def cache_embedding(
        self,
        *,
        checksum: str,
        provider: str,
        model: str,
        dimension: int,
        vector: list[float],
    ) -> EmbeddingCache:
        existing = await self._session.execute(
            select(EmbeddingCache).where(
                EmbeddingCache.content_checksum == checksum,
                EmbeddingCache.provider == provider,
                EmbeddingCache.model == model,
                EmbeddingCache.dimension == dimension,
            )
        )
        cached = existing.scalar_one_or_none()
        if cached is not None:
            return cached
        row = EmbeddingCache(
            content_checksum=checksum,
            provider=provider,
            model=model,
            dimension=dimension,
            vector=vector,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def record_retrievals(
        self,
        *,
        message_id: str,
        retrievals: list[dict[str, Any]],
    ) -> list[MessageRetrieval]:
        rows: list[MessageRetrieval] = []
        for item in retrievals:
            row = MessageRetrieval(
                message_id=message_id,
                chunk_id=item.get("chunk_id"),
                memory_id=item.get("memory_id"),
                citation_id=item["citation_id"],
                source_type=item["source_type"],
                score=item.get("score"),
                metadata_json=item.get("metadata", {}),
            )
            self._session.add(row)
            rows.append(row)
        await self._session.flush()
        return rows


class SqlAlchemyMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: str,
        memory_type: str,
        scope: str,
        title: str,
        content: str,
        checksum: str,
        project_id: str | None = None,
        conversation_id: str | None = None,
        source: str = "manual",
        source_message_id: str | None = None,
        importance: int = 3,
        pinned: bool = False,
        enabled: bool = True,
        expires_at: datetime | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        memory = Memory(
            user_id=user_id,
            memory_type=memory_type,
            scope=scope,
            project_id=project_id,
            conversation_id=conversation_id,
            title=title,
            content=content,
            source=source,
            source_message_id=source_message_id,
            importance=importance,
            pinned=pinned,
            enabled=enabled,
            checksum=checksum,
            expires_at=expires_at,
            tags=tags or [],
            metadata_json=metadata or {},
        )
        self._session.add(memory)
        await self._session.flush()
        await self.add_event(memory.id, "created", actor="user")
        return memory

    async def get(self, memory_id: str, user_id: str) -> Memory | None:
        result = await self._session.execute(
            select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_memories(
        self,
        user_id: str,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        memory_type: str | None = None,
        enabled: bool | None = None,
    ) -> tuple[list[Memory], int]:
        conditions = [Memory.user_id == user_id]
        if memory_type:
            conditions.append(Memory.memory_type == memory_type)
        if enabled is not None:
            conditions.append(Memory.enabled.is_(enabled))
        if search:
            pattern = f"%{search}%"
            conditions.append(or_(Memory.title.ilike(pattern), Memory.content.ilike(pattern)))
        count_result = await self._session.execute(
            select(func.count()).select_from(Memory).where(*conditions)
        )
        result = await self._session.execute(
            select(Memory)
            .where(*conditions)
            .order_by(Memory.pinned.desc(), Memory.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(count_result.scalar_one())

    async def active_for_user(self, user_id: str, *, limit: int = 200) -> list[Memory]:
        now = utc_now()
        result = await self._session.execute(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.enabled.is_(True),
                or_(Memory.expires_at.is_(None), Memory.expires_at > now),
            )
            .order_by(Memory.pinned.desc(), Memory.importance.desc(), Memory.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, memory: Memory, **updates: Any) -> Memory:
        for key, value in updates.items():
            if value is not None and hasattr(memory, key):
                setattr(memory, key, value)
        memory.updated_at = utc_now()
        await self._session.flush()
        await self.add_event(memory.id, "updated", actor="user", metadata={"fields": list(updates)})
        return memory

    async def delete(self, memory: Memory) -> None:
        await self.add_event(memory.id, "deleted", actor="user")
        await self._session.delete(memory)
        await self._session.flush()

    async def add_event(
        self,
        memory_id: str,
        event_type: str,
        *,
        actor: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEvent:
        event = MemoryEvent(
            memory_id=memory_id,
            event_type=event_type,
            actor=actor,
            metadata_json=metadata or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def stats(self, user_id: str) -> int:
        count = await self._session.scalar(
            select(func.count()).select_from(Memory).where(Memory.user_id == user_id)
        )
        return int(count or 0)


class SqlAlchemyAgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: str,
        slug: str,
        name: str,
        description: str,
        system_prompt: str,
        configuration: dict[str, Any],
        enabled: bool,
        built_in_origin: str | None = None,
    ) -> CustomAgent:
        agent = CustomAgent(
            user_id=user_id,
            slug=slug,
            name=name,
            description=description,
            system_prompt=system_prompt,
            configuration=configuration,
            enabled=enabled,
            built_in_origin=built_in_origin,
        )
        self._session.add(agent)
        await self._session.flush()
        return agent

    async def get(self, user_id: str, agent_id: str) -> CustomAgent | None:
        result = await self._session.execute(
            select(CustomAgent).where(
                CustomAgent.user_id == user_id,
                or_(CustomAgent.id == agent_id, CustomAgent.slug == agent_id),
            )
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[CustomAgent]:
        result = await self._session.execute(
            select(CustomAgent)
            .where(CustomAgent.user_id == user_id)
            .order_by(CustomAgent.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, agent: CustomAgent, **updates: Any) -> CustomAgent:
        for key, value in updates.items():
            if value is not None and hasattr(agent, key):
                setattr(agent, key, value)
        agent.updated_at = utc_now()
        await self._session.flush()
        return agent

    async def delete(self, agent: CustomAgent) -> None:
        await self._session.delete(agent)
        await self._session.flush()


class SqlAlchemyToolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_execution(
        self,
        *,
        user_id: str,
        tool_name: str,
        permission_class: str,
        status: str,
        input_payload: dict[str, Any],
        input_hash: str,
        conversation_id: str | None = None,
        message_id: str | None = None,
        agent_id: str | None = None,
        request_id: str | None = None,
        generation_id: str | None = None,
        working_directory: str | None = None,
        command_display: str | None = None,
    ) -> ToolExecution:
        execution = ToolExecution(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            agent_id=agent_id,
            request_id=request_id,
            generation_id=generation_id,
            tool_name=tool_name,
            permission_class=permission_class,
            status=status,
            input=input_payload,
            input_hash=input_hash,
            working_directory=working_directory,
            command_display=command_display,
            data={},
        )
        self._session.add(execution)
        await self._session.flush()
        return execution

    async def get_execution(self, user_id: str, execution_id: str) -> ToolExecution | None:
        result = await self._session.execute(
            select(ToolExecution).where(
                ToolExecution.id == execution_id,
                ToolExecution.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_executions(
        self, user_id: str, *, limit: int, offset: int
    ) -> tuple[list[ToolExecution], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(ToolExecution).where(ToolExecution.user_id == user_id)
        )
        result = await self._session.execute(
            select(ToolExecution)
            .where(ToolExecution.user_id == user_id)
            .order_by(ToolExecution.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(count_result.scalar_one())

    async def update_execution(self, execution: ToolExecution, **updates: Any) -> ToolExecution:
        for key, value in updates.items():
            if value is not None and hasattr(execution, key):
                setattr(execution, key, value)
        execution.updated_at = utc_now()
        await self._session.flush()
        return execution

    async def create_confirmation(
        self,
        *,
        execution_id: str,
        user_id: str,
        tool_name: str,
        permission_class: str,
        payload_hash: str,
        payload: dict[str, Any],
        risk_summary: str,
        expires_at: datetime,
    ) -> ToolConfirmation:
        confirmation = ToolConfirmation(
            execution_id=execution_id,
            user_id=user_id,
            tool_name=tool_name,
            permission_class=permission_class,
            status="pending",
            payload_hash=payload_hash,
            payload=payload,
            risk_summary=risk_summary,
            expires_at=expires_at,
        )
        self._session.add(confirmation)
        await self._session.flush()
        return confirmation

    async def get_confirmation(self, user_id: str, confirmation_id: str) -> ToolConfirmation | None:
        result = await self._session.execute(
            select(ToolConfirmation).where(
                ToolConfirmation.id == confirmation_id,
                ToolConfirmation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_confirmations(self, user_id: str) -> list[ToolConfirmation]:
        result = await self._session.execute(
            select(ToolConfirmation)
            .where(ToolConfirmation.user_id == user_id)
            .order_by(ToolConfirmation.created_at.desc())
            .limit(50)
        )
        return list(result.scalars().all())

    async def update_confirmation(
        self, confirmation: ToolConfirmation, **updates: Any
    ) -> ToolConfirmation:
        for key, value in updates.items():
            if value is not None and hasattr(confirmation, key):
                setattr(confirmation, key, value)
        confirmation.updated_at = utc_now()
        await self._session.flush()
        return confirmation


class SqlAlchemySecurityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_workspace(
        self,
        *,
        user_id: str,
        name: str,
        mode: str,
        description: str = "",
        active_scope_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityWorkspace:
        workspace = SecurityWorkspace(
            user_id=user_id,
            name=name,
            mode=mode,
            description=description,
            active_scope_id=active_scope_id,
            metadata_json=metadata or {},
        )
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def get_workspace(self, user_id: str, workspace_id: str) -> SecurityWorkspace | None:
        result = await self._session.execute(
            select(SecurityWorkspace).where(
                SecurityWorkspace.id == workspace_id,
                SecurityWorkspace.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_workspaces(self, user_id: str) -> list[SecurityWorkspace]:
        result = await self._session.execute(
            select(SecurityWorkspace)
            .where(SecurityWorkspace.user_id == user_id)
            .order_by(SecurityWorkspace.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update_workspace(
        self, workspace: SecurityWorkspace, **updates: Any
    ) -> SecurityWorkspace:
        for key, value in updates.items():
            if value is not None and hasattr(workspace, key):
                setattr(workspace, key, value)
        workspace.updated_at = utc_now()
        await self._session.flush()
        return workspace

    async def create_scope(
        self,
        *,
        user_id: str,
        name: str,
        scope_type: str,
        target: str,
        workspace_id: str | None = None,
        description: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityScope:
        scope = SecurityScope(
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            scope_type=scope_type,
            target=target,
            description=description,
            enabled=enabled,
            metadata_json=metadata or {},
        )
        self._session.add(scope)
        await self._session.flush()
        return scope

    async def list_scopes(
        self, user_id: str, *, workspace_id: str | None = None
    ) -> list[SecurityScope]:
        conditions = [SecurityScope.user_id == user_id]
        if workspace_id is not None:
            conditions.append(SecurityScope.workspace_id == workspace_id)
        result = await self._session.execute(
            select(SecurityScope)
            .where(*conditions)
            .order_by(SecurityScope.enabled.desc(), SecurityScope.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_scope(self, user_id: str, scope_id: str) -> SecurityScope | None:
        result = await self._session.execute(
            select(SecurityScope).where(
                SecurityScope.id == scope_id,
                SecurityScope.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_finding(
        self,
        *,
        user_id: str,
        title: str,
        severity: str,
        confidence: str,
        description: str,
        evidence: str,
        remediation: str,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        category: str | None = None,
        cwe: str | None = None,
        cve: str | None = None,
        affected_asset: str | None = None,
        references: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityFinding:
        finding = SecurityFinding(
            user_id=user_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            title=title,
            severity=severity,
            confidence=confidence,
            category=category,
            cwe=cwe,
            cve=cve,
            affected_asset=affected_asset,
            description=description,
            evidence=evidence,
            remediation=remediation,
            references=references or [],
            metadata_json=metadata or {},
        )
        self._session.add(finding)
        await self._session.flush()
        return finding

    async def list_findings(
        self,
        user_id: str,
        *,
        workspace_id: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SecurityFinding], int]:
        conditions = [SecurityFinding.user_id == user_id]
        if workspace_id is not None:
            conditions.append(SecurityFinding.workspace_id == workspace_id)
        if severity is not None:
            conditions.append(SecurityFinding.severity == severity)
        count_result = await self._session.execute(
            select(func.count()).select_from(SecurityFinding).where(*conditions)
        )
        result = await self._session.execute(
            select(SecurityFinding)
            .where(*conditions)
            .order_by(SecurityFinding.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(count_result.scalar_one())

    async def create_note(
        self,
        *,
        user_id: str,
        title: str,
        content: str,
        workspace_id: str | None = None,
        finding_id: str | None = None,
        tags: list[str] | None = None,
        references: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SecurityNote:
        note = SecurityNote(
            user_id=user_id,
            workspace_id=workspace_id,
            finding_id=finding_id,
            title=title,
            content=content,
            tags=tags or [],
            references=references or [],
            metadata_json=metadata or {},
        )
        self._session.add(note)
        await self._session.flush()
        return note

    async def list_notes(
        self, user_id: str, *, workspace_id: str | None = None
    ) -> list[SecurityNote]:
        conditions = [SecurityNote.user_id == user_id]
        if workspace_id is not None:
            conditions.append(SecurityNote.workspace_id == workspace_id)
        result = await self._session.execute(
            select(SecurityNote).where(*conditions).order_by(SecurityNote.updated_at.desc())
        )
        return list(result.scalars().all())


class SqlAlchemyResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        *,
        user_id: str,
        query: str,
        status: str,
        provider: str | None,
        answer: str = "",
        official_only: bool = False,
        filters: dict[str, Any] | None = None,
        diagnostics: dict[str, Any] | None = None,
    ) -> ResearchSession:
        session = ResearchSession(
            user_id=user_id,
            query=query,
            status=status,
            provider=provider,
            answer=answer,
            official_only=official_only,
            filters=filters or {},
            diagnostics=diagnostics or {},
        )
        self._session.add(session)
        await self._session.flush()
        return session

    async def update_session(self, session: ResearchSession, **updates: Any) -> ResearchSession:
        for key, value in updates.items():
            if value is not None and hasattr(session, key):
                setattr(session, key, value)
        session.updated_at = utc_now()
        await self._session.flush()
        return session

    async def get_session(self, user_id: str, session_id: str) -> ResearchSession | None:
        result = await self._session.execute(
            select(ResearchSession).where(
                ResearchSession.id == session_id,
                ResearchSession.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self, user_id: str, *, limit: int = 30, offset: int = 0
    ) -> tuple[list[ResearchSession], int]:
        count_result = await self._session.execute(
            select(func.count())
            .select_from(ResearchSession)
            .where(ResearchSession.user_id == user_id)
        )
        result = await self._session.execute(
            select(ResearchSession)
            .where(ResearchSession.user_id == user_id)
            .order_by(ResearchSession.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), int(count_result.scalar_one())

    async def create_source(
        self,
        *,
        user_id: str,
        citation_id: str,
        url: str,
        normalized_url: str,
        domain: str,
        title: str,
        excerpt: str,
        session_id: str | None = None,
        source_type: str = "web",
        reliability: str = "unknown",
        content_checksum: str | None = None,
        retrieved_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchSource:
        source = ResearchSource(
            user_id=user_id,
            session_id=session_id,
            citation_id=citation_id,
            url=url,
            normalized_url=normalized_url,
            domain=domain,
            title=title,
            source_type=source_type,
            reliability=reliability,
            excerpt=excerpt,
            content_checksum=content_checksum,
            retrieved_at=retrieved_at,
            metadata_json=metadata or {},
        )
        self._session.add(source)
        await self._session.flush()
        return source

    async def list_sources(self, session_id: str) -> list[ResearchSource]:
        result = await self._session.execute(
            select(ResearchSource)
            .where(ResearchSource.session_id == session_id)
            .order_by(ResearchSource.citation_id.asc())
        )
        return list(result.scalars().all())

    async def get_cache(self, normalized_url: str) -> ResearchCacheEntry | None:
        result = await self._session.execute(
            select(ResearchCacheEntry).where(ResearchCacheEntry.normalized_url == normalized_url)
        )
        return result.scalar_one_or_none()

    async def upsert_cache(
        self,
        *,
        normalized_url: str,
        url: str,
        domain: str,
        title: str,
        content_text: str,
        excerpt: str,
        checksum: str,
        retrieved_at: datetime,
        expires_at: datetime,
        mime_type: str | None = None,
        status_code: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchCacheEntry:
        existing = await self.get_cache(normalized_url)
        if existing is not None:
            existing.url = url
            existing.domain = domain
            existing.title = title
            existing.content_text = content_text
            existing.excerpt = excerpt
            existing.mime_type = mime_type
            existing.status_code = status_code
            existing.checksum = checksum
            existing.retrieved_at = retrieved_at
            existing.expires_at = expires_at
            existing.metadata_json = metadata or {}
            existing.updated_at = utc_now()
            await self._session.flush()
            return existing
        entry = ResearchCacheEntry(
            normalized_url=normalized_url,
            url=url,
            domain=domain,
            title=title,
            content_text=content_text,
            excerpt=excerpt,
            mime_type=mime_type,
            status_code=status_code,
            checksum=checksum,
            retrieved_at=retrieved_at,
            expires_at=expires_at,
            metadata_json=metadata or {},
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
