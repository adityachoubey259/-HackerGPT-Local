"""Document chunking strategies."""

from __future__ import annotations

from dataclasses import dataclass

from backend.rag.checksums import sha256_text
from backend.rag.models import DocumentChunkDraft, ParsedDocument, ParsedSection
from backend.rag.text import estimate_tokens, normalize_text


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    target_tokens: int = 420
    overlap_tokens: int = 60
    min_tokens: int = 30


class DocumentChunker:
    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()

    def chunk(
        self, document: ParsedDocument, *, tags: list[str] | None = None
    ) -> list[DocumentChunkDraft]:
        drafts: list[DocumentChunkDraft] = []
        for parsed_section in document.sections or [ParsedSection(text=document.content)]:
            drafts.extend(self._chunk_section(parsed_section, document, tags or []))
        merged = self._merge_tiny_chunks(drafts)
        return [
            draft.model_copy(
                update={
                    "chunk_index": index,
                    "metadata": draft.metadata | {"source_id": document.source_id},
                }
            )
            for index, draft in enumerate(merged)
        ]

    def _chunk_section(
        self,
        parsed_section: ParsedSection,
        document: ParsedDocument,
        tags: list[str],
    ) -> list[DocumentChunkDraft]:
        text = normalize_text(
            parsed_section.text,
            preserve_code=document.parser == "source_code",
        )
        if not text:
            return []
        paragraphs = split_units(text, preserve_code=document.parser == "source_code")
        chunks: list[DocumentChunkDraft] = []
        current: list[str] = []
        current_tokens = 0
        for unit in paragraphs:
            token_count = estimate_tokens(unit)
            if current and current_tokens + token_count > self._config.target_tokens:
                chunks.append(self._draft("\n\n".join(current), parsed_section, document, tags))
                current = overlap_tail(current, self._config.overlap_tokens)
                current_tokens = estimate_tokens("\n\n".join(current))
            if token_count > self._config.target_tokens:
                for piece in split_long_unit(unit, self._config.target_tokens):
                    chunks.append(self._draft(piece, parsed_section, document, tags))
                current = []
                current_tokens = 0
            else:
                current.append(unit)
                current_tokens += token_count
        if current:
            chunks.append(self._draft("\n\n".join(current), parsed_section, document, tags))
        return chunks

    def _draft(
        self,
        text: str,
        parsed_section: ParsedSection,
        document: ParsedDocument,
        tags: list[str],
    ) -> DocumentChunkDraft:
        normalized = normalize_text(text, preserve_code=document.parser == "source_code")
        return DocumentChunkDraft(
            text=normalized,
            chunk_index=0,
            page_number=parsed_section.page_number,
            section=parsed_section.heading,
            source_path=document.source_path,
            checksum=sha256_text(normalized),
            token_count=estimate_tokens(normalized),
            character_count=len(normalized),
            tags=tags,
            metadata={
                "parser": document.parser,
                "file_name": document.file_name,
                "line_start": parsed_section.line_start,
                "line_end": parsed_section.line_end,
            },
        )

    def _merge_tiny_chunks(self, chunks: list[DocumentChunkDraft]) -> list[DocumentChunkDraft]:
        if not chunks:
            return []
        merged: list[DocumentChunkDraft] = []
        pending: DocumentChunkDraft | None = None
        for chunk in chunks:
            if pending is None:
                pending = chunk
                continue
            if pending.token_count < self._config.min_tokens:
                text = f"{pending.text}\n\n{chunk.text}"
                pending = pending.model_copy(
                    update={
                        "text": text,
                        "checksum": sha256_text(text),
                        "token_count": estimate_tokens(text),
                        "character_count": len(text),
                    }
                )
            else:
                merged.append(pending)
                pending = chunk
        if pending is not None:
            merged.append(pending)
        return merged


def split_units(text: str, *, preserve_code: bool) -> list[str]:
    if preserve_code:
        lines = text.splitlines()
        units: list[str] = []
        current: list[str] = []
        for line in lines:
            if current and line and not line.startswith((" ", "\t", "}", ")", "]")):
                units.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            units.append("\n".join(current))
        return [unit for unit in units if unit.strip()]
    return [unit.strip() for unit in text.split("\n\n") if unit.strip()]


def split_long_unit(text: str, target_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    target_words = max(32, target_tokens * 3)
    return [
        " ".join(words[index : index + target_words])
        for index in range(0, len(words), target_words)
    ]


def overlap_tail(units: list[str], overlap_tokens: int) -> list[str]:
    selected: list[str] = []
    tokens = 0
    for unit in reversed(units):
        tokens += estimate_tokens(unit)
        if tokens > overlap_tokens and selected:
            break
        selected.append(unit)
    return list(reversed(selected))
