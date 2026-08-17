"""Knowledge ingestion and retrieval services."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api.errors import ApplicationError
from backend.api.schemas.knowledge import (
    DocumentChunkRead,
    DocumentDetailResponse,
    DocumentRead,
    IngestionJobRead,
    KnowledgeListResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeStatsResponse,
)
from backend.core.config import AppSettings
from backend.core.policy import PolicyConfig
from backend.core.time import utc_now
from backend.db.models import Document, DocumentChunk, IngestionJob
from backend.db.repositories.sqlalchemy import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyUserRepository,
)
from backend.rag.chunking import ChunkingConfig, DocumentChunker
from backend.rag.embeddings.registry import EmbeddingProviderRegistry
from backend.rag.models import DocumentStatus, IngestionJobStatus, RagContextPack, RetrievalFilter
from backend.rag.parsers import DocumentParseError, DocumentParserRegistry
from backend.rag.path_safety import (
    IngestionLimits,
    PathSafetyError,
    collect_candidates,
    sanitize_storage_name,
)
from backend.rag.retrieval import RetrievalConfig, RetrievalService
from backend.rag.vectorstores.protocols import VectorRecord
from backend.rag.vectorstores.registry import VectorStoreRegistry


class KnowledgeService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: AppSettings,
        policy: PolicyConfig,
        embeddings: EmbeddingProviderRegistry,
        vector_stores: VectorStoreRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._policy = policy
        self._parsers = DocumentParserRegistry()
        self._chunker = DocumentChunker(
            ChunkingConfig(
                target_tokens=policy.rag_policy.chunk_target_tokens,
                overlap_tokens=policy.rag_policy.chunk_overlap_tokens,
            )
        )
        self._embeddings = embeddings
        self._vector_stores = vector_stores
        self._retrieval = RetrievalService(
            session_factory,
            embeddings,
            vector_stores,
            config=RetrievalConfig(
                max_chunks=policy.rag_policy.maximum_retrieved_chunks,
                min_relevance=policy.rag_policy.minimum_relevance,
                context_token_budget=policy.rag_policy.context_token_budget,
            ),
        )

    async def list_documents(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
        status: str | None,
    ) -> KnowledgeListResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            documents, total = await SqlAlchemyDocumentRepository(session).list_documents(
                user.id,
                limit=limit,
                offset=offset,
                search=search,
                status=status,
            )
        return KnowledgeListResponse(
            items=[document_to_read(item) for item in documents], total=total
        )

    async def detail(self, document_id: str) -> DocumentDetailResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemyDocumentRepository(session)
            document = await repo.get_document(document_id, user.id)
            if document is None:
                raise not_found()
            chunks = await repo.list_chunks(document.id)
        return DocumentDetailResponse(
            document=document_to_read(document),
            chunks=[chunk_to_read(chunk) for chunk in chunks],
        )

    async def ingest_upload(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None,
        tags: list[str],
    ) -> IngestionJobRead:
        if len(content) > self._policy.rag_policy.upload_max_bytes:
            raise ApplicationError(
                "UPLOAD_TOO_LARGE",
                "Uploaded file exceeds the configured limit.",
                status_code=413,
            )
        safe_name = sanitize_storage_name(filename)
        storage = self._settings.paths.knowledge_dir / "uploads"
        storage.mkdir(parents=True, exist_ok=True)
        destination = storage / f"{uuid.uuid4()}-{safe_name}"
        destination.write_bytes(content)
        try:
            return await self._ingest_file(
                destination, source="upload", mime_type=mime_type, tags=tags
            )
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    async def ingest_path(self, path: str, *, tags: list[str]) -> list[IngestionJobRead]:
        limits = self._limits()
        try:
            candidates = collect_candidates(Path(path), limits)
        except PathSafetyError as exc:
            raise ApplicationError(exc.code, str(exc), status_code=400) from exc
        jobs: list[IngestionJobRead] = []
        for candidate in candidates:
            jobs.append(
                await self._ingest_file(
                    candidate.path, source="path", mime_type=candidate.mime_type, tags=tags
                )
            )
        return jobs

    async def reindex(self, document_id: str) -> IngestionJobRead:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            document = await SqlAlchemyDocumentRepository(session).get_document(
                document_id, user.id
            )
            if document is None:
                raise not_found()
            if not document.source_path:
                raise ApplicationError(
                    "SOURCE_PATH_MISSING",
                    "Document source path is unavailable.",
                    status_code=400,
                )
            path = Path(document.source_path)
        return await self._ingest_file(
            path, source="reindex", mime_type=document.mime_type, tags=document.tags
        )

    async def delete(self, document_id: str) -> None:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemyDocumentRepository(session)
            document = await repo.get_document(document_id, user.id)
            if document is None:
                raise not_found()
            chunks = await repo.list_chunks(document.id)
            await repo.delete_document(document)
            await session.commit()
        await self._vector_stores.get("faiss").delete([chunk.id for chunk in chunks])

    async def search(self, request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
        pack = await self._retrieval.retrieve(
            user.id,
            request.query,
            filters=RetrievalFilter(document_ids=request.document_ids, tags=request.tags),
        )
        return KnowledgeSearchResponse(
            items=[
                KnowledgeSearchResult(
                    chunk_id=item.chunk_id,
                    document_id=item.document_id,
                    citation_id=item.citation_id,
                    text=item.text,
                    score=item.score,
                    file_name=item.file_name,
                    source_path=item.source_path,
                    page_number=item.page_number,
                    section=item.section,
                    metadata=item.metadata,
                )
                for item in pack.results
            ],
            citations=[item.model_dump() for item in pack.citations],
            diagnostics=pack.diagnostics,
        )

    async def stats(self) -> KnowledgeStatsResponse:
        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            document_count, chunk_count = await SqlAlchemyDocumentRepository(session).stats(user.id)
        embedding = self._embeddings.get("local")
        store = self._vector_stores.get("faiss")
        return KnowledgeStatsResponse(
            document_count=document_count,
            chunk_count=chunk_count,
            embedding_provider=embedding.provider_id,
            embedding_model=embedding.model_id,
            vector_store=store.store_id,
            vector_store_status=await store.health(),
        )

    async def retrieve_context(self, user_id: str, query: str) -> RagContextPack | None:
        if not self._policy.rag_policy.enabled:
            return None
        return await self._retrieval.retrieve(user_id, query)

    async def _ingest_file(
        self,
        path: Path,
        *,
        source: str,
        mime_type: str | None,
        tags: list[str],
    ) -> IngestionJobRead:
        limits = self._limits()
        try:
            candidate = collect_candidates(path, limits)[0]
        except (IndexError, PathSafetyError) as exc:
            code = exc.code if isinstance(exc, PathSafetyError) else "NO_INGESTION_CANDIDATE"
            raise ApplicationError(
                code,
                "No safe ingestible file was found.",
                status_code=400,
            ) from exc

        async with self._session_factory() as session:
            user = await SqlAlchemyUserRepository(session).get_or_create_local()
            repo = SqlAlchemyDocumentRepository(session)
            document = await repo.create_document(
                user_id=user.id,
                name=candidate.display_name,
                source=source,
                source_path=str(candidate.path),
                mime_type=mime_type,
                size_bytes=candidate.size_bytes,
                checksum=candidate.checksum,
                status=DocumentStatus.INDEXING.value,
                tags=tags,
            )
            job = await repo.create_job(user_id=user.id, source=source, document_id=document.id)
            await repo.update_job(job, status=IngestionJobStatus.RUNNING.value)
            await session.commit()

        try:
            parser = self._parsers.resolve(candidate.path, mime_type)
            parsed = parser.parse(candidate.path, source_id=document.id, mime_type=mime_type)
            chunks = self._chunker.chunk(parsed, tags=tags)
            provider = self._embeddings.get(self._policy.rag_policy.embedding_provider)
            embeddings = await provider.embed_texts([chunk.text for chunk in chunks])
            dimension = embeddings[0].dimension if embeddings else provider.dimension
            async with self._session_factory() as session:
                repo = SqlAlchemyDocumentRepository(session)
                document_row = await repo.get_document(document.id, user.id)
                job_row = await session.get(IngestionJob, job.id)
                if document_row is None or job_row is None:
                    raise ApplicationError(
                        "INGESTION_STATE_MISSING",
                        "Ingestion state was lost.",
                        status_code=500,
                    )
                created_chunks = await repo.replace_chunks(
                    document_row,
                    chunks,
                    embedding_provider=provider.provider_id,
                    embedding_model=provider.model_id,
                    embedding_dimension=dimension,
                )
                for embedded in embeddings:
                    await repo.cache_embedding(
                        checksum=embedded.checksum,
                        provider=embedded.provider,
                        model=embedded.model,
                        dimension=embedded.dimension,
                        vector=embedded.vector,
                    )
                await repo.update_document(
                    document_row,
                    status=DocumentStatus.INDEXED.value,
                    parser=parsed.parser,
                    title=parsed.title,
                    indexed_at=utc_now(),
                    metadata=parsed.metadata | {"warnings": parsed.warnings},
                )
                await repo.update_job(
                    job_row,
                    status=IngestionJobStatus.COMPLETED.value,
                    processed_files=1,
                    chunks_indexed=len(created_chunks),
                )
                await session.commit()
            await self._vector_stores.get(self._policy.rag_policy.vector_store).upsert(
                [
                    VectorRecord(
                        id=chunk.id,
                        vector=embedding.vector,
                        metadata={
                            "user_id": user.id,
                            "document_id": chunk.document_id,
                            "chunk_id": chunk.id,
                            "citation_id": chunk.citation_id,
                        },
                    )
                    for chunk, embedding in zip(created_chunks, embeddings, strict=False)
                ],
                dimension=dimension,
            )
        except DocumentParseError as exc:
            await self._mark_failed(document.id, job.id, exc.code, str(exc))
        except Exception as exc:
            await self._mark_failed(document.id, job.id, "INGESTION_FAILED", str(exc))
            raise

        async with self._session_factory() as session:
            job_row = await session.get(IngestionJob, job.id)
            if job_row is None:
                raise ApplicationError(
                    "INGESTION_JOB_NOT_FOUND",
                    "Ingestion job was not found.",
                    status_code=500,
                )
            return job_to_read(job_row)

    async def _mark_failed(self, document_id: str, job_id: str, code: str, message: str) -> None:
        async with self._session_factory() as session:
            repo = SqlAlchemyDocumentRepository(session)
            document = await session.get(Document, document_id)
            job = await session.get(IngestionJob, job_id)
            if document is not None:
                await repo.update_document(
                    document,
                    status=DocumentStatus.FAILED.value,
                    failure_code=code,
                    failure_message=message,
                )
            if job is not None:
                await repo.update_job(
                    job,
                    status=IngestionJobStatus.FAILED.value,
                    failure_code=code,
                    failure_message=message,
                )
            await session.commit()

    def _limits(self) -> IngestionLimits:
        roots = tuple(
            Path(root).resolve(strict=False)
            for root in self._policy.rag_policy.allowed_ingestion_roots
        )
        configured_roots = roots or (Path(".").resolve(strict=False),)
        return IngestionLimits(
            max_file_size_bytes=self._policy.rag_policy.upload_max_bytes,
            allowed_extensions=frozenset(
                extension.lower() for extension in self._policy.rag_policy.allowed_file_types
            ),
            allowed_roots=(
                *configured_roots,
                self._settings.paths.knowledge_dir.resolve(strict=False),
                self._settings.paths.uploads_dir.resolve(strict=False),
            ),
        )


def document_to_read(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        name=document.name,
        source=document.source,
        source_path=document.source_path,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        checksum=document.checksum,
        status=DocumentStatus(document.status),
        parser=document.parser,
        title=document.title,
        tags=document.tags,
        metadata=document.metadata_json,
        failure_code=document.failure_code,
        failure_message=document.failure_message,
        indexed_at=document.indexed_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def chunk_to_read(chunk: DocumentChunk) -> DocumentChunkRead:
    return DocumentChunkRead(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_index=chunk.chunk_index,
        citation_id=chunk.citation_id,
        text=chunk.text,
        page_number=chunk.page_number,
        section=chunk.section,
        token_count=chunk.token_count,
        character_count=chunk.character_count,
        tags=chunk.tags,
        metadata=chunk.metadata_json,
        created_at=chunk.created_at,
    )


def job_to_read(job: IngestionJob) -> IngestionJobRead:
    return IngestionJobRead(
        id=job.id,
        document_id=job.document_id,
        source=job.source,
        status=IngestionJobStatus(job.status),
        total_files=job.total_files,
        processed_files=job.processed_files,
        chunks_indexed=job.chunks_indexed,
        failure_code=job.failure_code,
        failure_message=job.failure_message,
        metadata=job.metadata_json,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def not_found() -> ApplicationError:
    return ApplicationError("DOCUMENT_NOT_FOUND", "Document was not found.", status_code=404)
