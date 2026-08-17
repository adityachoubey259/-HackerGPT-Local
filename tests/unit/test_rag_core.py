from __future__ import annotations

from pathlib import Path

import pytest

from backend.rag.chunking import ChunkingConfig, DocumentChunker
from backend.rag.embeddings.local import LocalHashEmbeddingProvider
from backend.rag.models import RetrievalResult
from backend.rag.parsers.text import MarkdownParser
from backend.rag.path_safety import (
    IngestionLimits,
    PathSafetyError,
    collect_candidates,
    sanitize_storage_name,
)
from backend.rag.retrieval import pack_context
from backend.rag.vectorstores.faiss_store import DimensionMismatchError, LocalFaissVectorStore
from backend.rag.vectorstores.protocols import VectorRecord


def test_markdown_parser_and_chunker_preserve_sections(tmp_path: Path) -> None:
    source = tmp_path / "runtime-notes.md"
    source.write_text(
        "# GPU Notes\n\nCUDA should stay local.\n\n"
        "## Routing\n\nPrefer local retrieval citations over ungrounded answers.\n",
        encoding="utf-8",
    )

    parsed = MarkdownParser().parse(source, source_id="doc-1")
    chunks = DocumentChunker(ChunkingConfig(target_tokens=8, overlap_tokens=2, min_tokens=1)).chunk(
        parsed,
        tags=["local"],
    )

    assert parsed.parser == "markdown"
    assert [section.heading for section in parsed.sections] == ["GPU Notes", "Routing"]
    assert chunks
    assert chunks[0].metadata["source_id"] == "doc-1"
    assert chunks[0].tags == ["local"]
    assert all(chunk.checksum for chunk in chunks)


def test_path_safety_enforces_roots_extensions_and_storage_names(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    blocked = tmp_path / "blocked"
    allowed.mkdir()
    blocked.mkdir()
    safe_file = allowed / "notes.txt"
    unsafe_file = blocked / "secrets.txt"
    ignored_file = allowed / "node_modules" / "package.txt"
    safe_file.write_text("local knowledge", encoding="utf-8")
    unsafe_file.write_text("outside root", encoding="utf-8")
    ignored_file.parent.mkdir()
    ignored_file.write_text("ignored dependency", encoding="utf-8")
    limits = IngestionLimits(
        max_file_size_bytes=1000,
        allowed_extensions=frozenset({".txt"}),
        allowed_roots=(allowed,),
    )

    candidates = collect_candidates(allowed, limits)

    assert [candidate.display_name for candidate in candidates] == ["notes.txt"]
    assert sanitize_storage_name("../unsafe name?.md") == "unsafe_name_.md"
    with pytest.raises(PathSafetyError):
        collect_candidates(unsafe_file, limits)


@pytest.mark.asyncio
async def test_local_vector_store_filters_persists_and_checks_dimensions(tmp_path: Path) -> None:
    store_path = tmp_path / "faiss_index.json"
    store = LocalFaissVectorStore(store_path)
    await store.upsert(
        [
            VectorRecord("chunk-a", [1.0, 0.0, 0.0], {"user_id": "u1"}),
            VectorRecord("chunk-b", [0.0, 1.0, 0.0], {"user_id": "u2"}),
        ],
        dimension=3,
    )

    hits = await LocalFaissVectorStore(store_path).search(
        [1.0, 0.0, 0.0],
        limit=5,
        filters={"user_id": "u1"},
    )

    assert [hit.id for hit in hits] == ["chunk-a"]
    assert hits[0].score == 1.0
    with pytest.raises(DimensionMismatchError):
        await store.search([1.0, 0.0], limit=1)


@pytest.mark.asyncio
async def test_local_hash_embeddings_are_deterministic() -> None:
    provider = LocalHashEmbeddingProvider()
    first, second = await provider.embed_texts(["CUDA local runtime", "CUDA local runtime"])

    assert first.vector == second.vector
    assert len(first.vector) == provider.dimension
    assert first.provider == "local"


def test_pack_context_assigns_stable_citations_with_budget() -> None:
    results = [
        RetrievalResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            citation_id="[old]",
            text="Local RAG stores retrieved chunks as untrusted context.",
            score=0.91,
            lexical_score=0.5,
            vector_score=0.96,
            file_name="rag.md",
            source_path=None,
            page_number=2,
            section="Security",
            metadata={},
        )
    ]

    pack = pack_context(results, token_budget=80)

    assert pack.results[0].citation_id == "[K1]"
    assert pack.citations[0].citation_id == "[K1]"
    assert "rag.md page 2 section Security" in pack.context_text
