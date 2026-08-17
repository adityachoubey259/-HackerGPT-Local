"""Parser registry."""

from __future__ import annotations

from pathlib import Path

from backend.rag.parsers.base import BaseDocumentParser, DocumentParseError
from backend.rag.parsers.text import default_parsers


class DocumentParserRegistry:
    def __init__(self, parsers: list[BaseDocumentParser] | None = None) -> None:
        self._parsers = parsers or default_parsers()

    @property
    def allowed_extensions(self) -> set[str]:
        extensions: set[str] = set()
        for parser in self._parsers:
            extensions.update(parser.supported_extensions)
        return extensions

    def resolve(self, path: Path, mime_type: str | None = None) -> BaseDocumentParser:
        for parser in self._parsers:
            if parser.can_parse(path, mime_type):
                return parser
        raise DocumentParseError(
            f"Unsupported document type: {path.suffix or path.name}",
            code="UNSUPPORTED_DOCUMENT_TYPE",
        )
