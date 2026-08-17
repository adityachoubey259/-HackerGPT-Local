"""Universal code block model and parsing utilities."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from backend.core.languages import normalize_language_label


class CodeDiagnostic(BaseModel):
    line: int | None = None
    column: int | None = None
    message: str
    severity: str = "error"  # error, warning, info


class CodeBlock(BaseModel):
    language: str
    raw_language_label: str
    source: str
    ordinal: int = 0
    filename: str | None = None
    validation_status: str = "UNSUPPORTED"
    diagnostics: list[CodeDiagnostic] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


_FENCE_REGEX = re.compile(
    r"^```([^\n`]*)\n([\s\S]*?)\n```$",
    re.MULTILINE,
)

_FILENAME_PATTERNS = [
    re.compile(r'^(?:file|filename|title)=["\']?([^\s"\']+)["\']?', re.IGNORECASE),
    re.compile(r"^(?://|#|/\*|<!--|;)\s*(?:file|filename|filepath):\s*([^\s\*]+)", re.IGNORECASE),
]


def normalize_source_newlines(code: str) -> str:
    """Normalize CRLF to LF without altering any other whitespace or characters."""
    return code.replace("\r\n", "\n")


def extract_code_blocks(markdown: str) -> list[CodeBlock]:
    """Extract code blocks from markdown fences without mutating logical source."""
    blocks: list[CodeBlock] = []
    ordinal = 0

    for match in _FENCE_REGEX.finditer(markdown):
        raw_label = match.group(1).strip()
        raw_source = match.group(2)
        source = normalize_source_newlines(raw_source)

        filename: str | None = None
        label_parts = raw_label.split(maxsplit=1)
        lang_tag = label_parts[0] if label_parts else ""

        if len(label_parts) > 1:
            meta_str = label_parts[1]
            for fn_pattern in _FILENAME_PATTERNS:
                m = fn_pattern.search(meta_str)
                if m:
                    filename = m.group(1)
                    break

        if not filename:
            first_line = source.split("\n", 1)[0].strip()
            for fn_pattern in _FILENAME_PATTERNS:
                m = fn_pattern.search(first_line)
                if m:
                    filename = m.group(1)
                    break

        normalized_lang = normalize_language_label(lang_tag or "text")

        blocks.append(
            CodeBlock(
                language=normalized_lang,
                raw_language_label=raw_label,
                source=source,
                ordinal=ordinal,
                filename=filename,
                validation_status="UNSUPPORTED",
            )
        )
        ordinal += 1

    return blocks
