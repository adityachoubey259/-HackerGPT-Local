"""Document parser protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from backend.rag.models import ParsedDocument


class DocumentParseError(Exception):
    def __init__(self, message: str, *, code: str = "PARSE_FAILED") -> None:
        super().__init__(message)
        self.code = code


class BaseDocumentParser(Protocol):
    parser_id: str
    supported_extensions: frozenset[str]

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool: ...
    def parse(
        self, path: Path, *, source_id: str, mime_type: str | None = None
    ) -> ParsedDocument: ...
