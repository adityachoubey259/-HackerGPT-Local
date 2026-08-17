"""Text, Markdown, JSON, CSV, HTML, DOCX, PDF, and source parsers."""

from __future__ import annotations

import csv
import json
import mimetypes
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from defusedxml import ElementTree

from backend.rag.checksums import sha256_file
from backend.rag.models import ParsedDocument, ParsedSection
from backend.rag.parsers.base import DocumentParseError
from backend.rag.text import normalize_text

TEXT_EXTENSIONS = frozenset({".txt", ".text", ".log"})
MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown", ".mdx"})
HTML_EXTENSIONS = frozenset({".html", ".htm"})
JSON_EXTENSIONS = frozenset({".json", ".jsonl"})
CSV_EXTENSIONS = frozenset({".csv", ".tsv"})
DOCX_EXTENSIONS = frozenset({".docx"})
PDF_EXTENSIONS = frozenset({".pdf"})
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".cc",
        ".java",
        ".sh",
        ".bash",
        ".ps1",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
    }
)


class PlainTextParser:
    parser_id = "text"
    supported_extensions = TEXT_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions or (mime_type or "").startswith(
            "text/"
        )

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        text = normalize_text(read_text(path))
        return parsed(path, source_id, mime_type, self.parser_id, text, [section(text)])


class MarkdownParser:
    parser_id = "markdown"
    supported_extensions = MARKDOWN_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        text = normalize_text(read_text(path), preserve_code=True)
        sections = markdown_sections(text)
        return parsed(path, source_id, mime_type, self.parser_id, text, sections)


class HtmlParser:
    parser_id = "html"
    supported_extensions = HTML_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions or mime_type == "text/html"

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        extractor = _ReadableHtmlParser()
        extractor.feed(read_text(path))
        text = normalize_text("\n".join(extractor.blocks))
        return parsed(path, source_id, mime_type, self.parser_id, text, [section(text)])


class JsonParser:
    parser_id = "json"
    supported_extensions = JSON_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions or mime_type == "application/json"

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        raw = read_text(path)
        try:
            if path.suffix.lower() == ".jsonl":
                lines = [json.loads(line) for line in raw.splitlines() if line.strip()]
                text = "\n".join(
                    flatten_json(item, f"$[{index}]") for index, item in enumerate(lines)
                )
            else:
                text = flatten_json(json.loads(raw), "$")
        except json.JSONDecodeError as exc:
            raise DocumentParseError("JSON could not be parsed.", code="MALFORMED_JSON") from exc
        text = normalize_text(text)
        return parsed(path, source_id, mime_type, self.parser_id, text, [section(text)])


class CsvParser:
    parser_id = "csv"
    supported_extensions = CSV_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions or mime_type == "text/csv"

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        rows: list[str] = []
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            headers = reader.fieldnames or []
            rows.append(f"Headers: {', '.join(headers)}")
            for index, row in enumerate(reader, start=1):
                values = [f"{key}={value}" for key, value in row.items()]
                rows.append(f"Row {index}: " + "; ".join(values))
        text = normalize_text("\n".join(rows))
        return parsed(path, source_id, mime_type, self.parser_id, text, csv_sections(rows))


class SourceCodeParser:
    parser_id = "source_code"
    supported_extensions = CODE_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        text = normalize_text(read_text(path), preserve_code=True)
        return parsed(path, source_id, mime_type, self.parser_id, text, code_sections(text))


class DocxParser:
    parser_id = "docx"
    supported_extensions = DOCX_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        try:
            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml")
                core = (
                    archive.read("docProps/core.xml")
                    if "docProps/core.xml" in archive.namelist()
                    else b""
                )
        except (KeyError, zipfile.BadZipFile) as exc:
            raise DocumentParseError("DOCX could not be parsed.", code="MALFORMED_DOCX") from exc
        sections = docx_sections(xml)
        title = docx_title(core) or (
            sections[0].heading if sections and sections[0].heading else None
        )
        text = normalize_text("\n\n".join(item.text for item in sections))
        return parsed(path, source_id, mime_type, self.parser_id, text, sections, title=title)


class PdfParser:
    parser_id = "pdf"
    supported_extensions = PDF_EXTENSIONS

    def can_parse(self, path: Path, mime_type: str | None = None) -> bool:
        return path.suffix.lower() in self.supported_extensions or mime_type == "application/pdf"

    def parse(self, path: Path, *, source_id: str, mime_type: str | None = None) -> ParsedDocument:
        sections, metadata = try_pypdf(path)
        warnings: list[str] = []
        if not sections:
            sections = fallback_pdf_sections(path)
            if not sections:
                raise DocumentParseError(
                    "PDF has no extractable text and may be scanned.",
                    code="PDF_TEXT_UNAVAILABLE",
                )
            warnings.append("Used basic PDF text fallback; page structure may be approximate.")
        text = normalize_text("\n\n".join(item.text for item in sections))
        return parsed(
            path,
            source_id,
            mime_type,
            self.parser_id,
            text,
            sections,
            metadata=metadata,
            warnings=warnings,
        )


def parser_for_extension(
    extension: str,
) -> (
    PlainTextParser
    | MarkdownParser
    | HtmlParser
    | JsonParser
    | CsvParser
    | SourceCodeParser
    | DocxParser
    | PdfParser
    | None
):
    for parser in default_parsers():
        if extension.lower() in parser.supported_extensions:
            return parser
    return None


def default_parsers() -> list[
    PlainTextParser
    | MarkdownParser
    | HtmlParser
    | JsonParser
    | CsvParser
    | SourceCodeParser
    | DocxParser
    | PdfParser
]:
    return [
        MarkdownParser(),
        HtmlParser(),
        JsonParser(),
        CsvParser(),
        SourceCodeParser(),
        DocxParser(),
        PdfParser(),
        PlainTextParser(),
    ]


def read_text(path: Path) -> str:
    if path.stat().st_size == 0:
        raise DocumentParseError("File is empty.", code="EMPTY_FILE")
    return path.read_text(encoding="utf-8", errors="replace")


def parsed(
    path: Path,
    source_id: str,
    mime_type: str | None,
    parser_id: str,
    text: str,
    sections: list[ParsedSection],
    *,
    title: str | None = None,
    metadata: dict[str, str] | None = None,
    warnings: list[str] | None = None,
) -> ParsedDocument:
    guessed_type = mime_type or mimetypes.guess_type(path.name)[0]
    return ParsedDocument(
        source_id=source_id,
        file_name=path.name,
        source_path=str(path),
        mime_type=guessed_type,
        title=title,
        content=text,
        sections=sections or [section(text)],
        parser=parser_id,
        checksum=sha256_file(path),
        size_bytes=path.stat().st_size,
        metadata=metadata or {},
        warnings=warnings or [],
    )


def section(
    text: str,
    *,
    page_number: int | None = None,
    heading: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
) -> ParsedSection:
    return ParsedSection(
        text=text,
        page_number=page_number,
        heading=heading,
        line_start=line_start,
        line_end=line_end,
    )


def markdown_sections(text: str) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    current: list[str] = []
    heading: str | None = None
    start = 1
    lines = text.splitlines()
    in_code = False
    for index, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and line.startswith("#"):
            if current:
                sections.append(
                    section(
                        "\n".join(current), heading=heading, line_start=start, line_end=index - 1
                    )
                )
            heading = line.lstrip("#").strip() or None
            current = [line]
            start = index
        else:
            current.append(line)
    if current:
        sections.append(
            section("\n".join(current), heading=heading, line_start=start, line_end=len(lines))
        )
    return [item for item in sections if item.text.strip()]


def code_sections(text: str) -> list[ParsedSection]:
    lines = text.splitlines()
    boundaries = [1]
    pattern = re.compile(
        r"^\s*("
        r"def |class |async def |function |export function |pub fn |fn |func |"
        r"package |import "
        r")"
    )
    for index, line in enumerate(lines, start=1):
        if index > 1 and pattern.search(line):
            boundaries.append(index)
    boundaries.append(len(lines) + 1)
    sections: list[ParsedSection] = []
    for start, end in zip(boundaries, boundaries[1:], strict=False):
        block = "\n".join(lines[start - 1 : end - 1]).strip()
        if block:
            heading = first_non_empty(block)
            sections.append(section(block, heading=heading, line_start=start, line_end=end - 1))
    return sections or [section(text, line_start=1, line_end=len(lines))]


def csv_sections(rows: list[str], group_size: int = 25) -> list[ParsedSection]:
    sections: list[ParsedSection] = []
    header = rows[0] if rows else ""
    for start in range(1, len(rows), group_size):
        grouped = [header, *rows[start : start + group_size]]
        sections.append(
            section(
                "\n".join(grouped),
                heading=f"Rows {start}-{min(len(rows) - 1, start + group_size - 1)}",
                line_start=start,
                line_end=min(len(rows) - 1, start + group_size - 1),
            )
        )
    return sections or [section(header)]


def flatten_json(value: object, path: str) -> str:
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            lines.append(flatten_json(child, f"{path}.{key}"))
        return "\n".join(lines)
    if isinstance(value, list):
        return "\n".join(
            flatten_json(child, f"{path}[{index}]") for index, child in enumerate(value)
        )
    return f"{path}: {value}"


def docx_sections(xml: bytes) -> list[ParsedSection]:
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    sections: list[ParsedSection] = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        paragraph_text = normalize_text("".join(texts))
        if paragraph_text:
            style = paragraph.find(".//w:pStyle", namespace)
            style_value = (
                style.attrib.get(f"{{{namespace['w']}}}val") if style is not None else None
            )
            heading = (
                paragraph_text
                if style_value and style_value.lower().startswith("heading")
                else None
            )
            sections.append(section(paragraph_text, heading=heading))
    for table in root.findall(".//w:tbl", namespace):
        rows: list[str] = []
        for row in table.findall(".//w:tr", namespace):
            cells: list[str] = []
            for cell in row.findall(".//w:tc", namespace):
                cell_text = " ".join(node.text or "" for node in cell.findall(".//w:t", namespace))
                cells.append(normalize_text(cell_text))
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            sections.append(section("\n".join(rows), heading="Table"))
    return sections


def docx_title(core_xml: bytes) -> str | None:
    if not core_xml:
        return None
    try:
        root = ElementTree.fromstring(core_xml)
    except ElementTree.ParseError:
        return None
    for element in root.iter():
        if element.tag.endswith("title") and element.text:
            return normalize_text(element.text)
    return None


def try_pypdf(path: Path) -> tuple[list[ParsedSection], dict[str, str]]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError:
        return [], {}
    try:
        reader = PdfReader(str(path))
        metadata = {
            str(key).lstrip("/"): str(value) for key, value in (reader.metadata or {}).items()
        }
        sections = []
        for index, page in enumerate(reader.pages, start=1):
            text = normalize_text(page.extract_text() or "")
            if text:
                sections.append(section(text, page_number=index, heading=f"Page {index}"))
        return sections, metadata
    except Exception as exc:
        raise DocumentParseError("PDF could not be parsed.", code="MALFORMED_PDF") from exc


def fallback_pdf_sections(path: Path) -> list[ParsedSection]:
    data = path.read_bytes()
    extracted: list[str] = []
    for match in re.finditer(rb"\((.*?)\)\s*Tj", data, flags=re.DOTALL):
        extracted.append(match.group(1).decode("latin-1", errors="ignore"))
    for match in re.finditer(rb"\[(.*?)\]\s*TJ", data, flags=re.DOTALL):
        parts = re.findall(rb"\((.*?)\)", match.group(1), flags=re.DOTALL)
        if parts:
            extracted.append("".join(part.decode("latin-1", errors="ignore") for part in parts))
    text = normalize_text("\n".join(extracted))
    return [section(text, page_number=1, heading="Page 1")] if text else []


def first_non_empty(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:180]
    return None


class _ReadableHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored = 0
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "template"}:
            self._ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "template"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored:
            return
        text = normalize_text(data)
        if text:
            self.blocks.append(text)
