"""Centralized, extensible safe multi-language validator framework.

ENFORCES THE SAFE VALIDATION INVARIANT:
- NO CODE EXECUTION: Generated code is NEVER executed for validation.
- PREFERRED CHECKS: AST parsing, syntax checking, compile-only mode, schema parsing.
- SUBPROCESS ISOLATION: Controlled temp directories, argv arrays, strict timeouts,
  bounded output, sanitized environments, and sanitized diagnostic paths.
"""

from __future__ import annotations

import ast
import html.parser
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from abc import ABC, abstractmethod
from enum import StrEnum
from pathlib import Path
from typing import Any

import defusedxml.minidom
import yaml
from pydantic import BaseModel, Field

from backend.core.code_model import CodeDiagnostic
from backend.core.languages import normalize_language_label


class ValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    SKIPPED = "SKIPPED"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    ERROR = "ERROR"


class ValidationResult(BaseModel):
    status: ValidationStatus
    validator: str
    language: str
    diagnostics: list[CodeDiagnostic] = Field(default_factory=list)
    parse_success: bool | None = None
    compile_success: bool | None = None
    skipped_reason: str | None = None
    duration_ms: float = 0.0
    tool_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


def sanitize_diagnostic_path(raw_message: str, temp_dir: Path | str) -> str:
    """Strip internal host temporary paths from diagnostic error messages."""
    temp_str = str(temp_dir).rstrip("/\\")
    sanitized = raw_message.replace(temp_str, "<temp>")
    if os.name == "nt":
        sanitized = sanitized.replace(temp_str.replace("/", "\\"), "<temp>")
    return sanitized


def run_safe_validator_subprocess(
    cmd: list[str],
    *,
    source_file: Path | None = None,
    temp_dir: Path | None = None,
    timeout: float = 3.0,
    max_output_bytes: int = 10240,
) -> tuple[int, str, str, bool]:
    """Execute a safe external validator command in an isolated environment.

    Returns: (returncode, stdout, stderr, timed_out)
    """
    env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TMP": str(temp_dir) if temp_dir else os.environ.get("TMP", ""),
        "TEMP": str(temp_dir) if temp_dir else os.environ.get("TEMP", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }

    cwd = temp_dir if temp_dir else Path.cwd()

    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout = proc.stdout[:max_output_bytes]
        stderr = proc.stderr[:max_output_bytes]
        if temp_dir:
            stdout = sanitize_diagnostic_path(stdout, temp_dir)
            stderr = sanitize_diagnostic_path(stderr, temp_dir)
        return proc.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        return -1, "", "Validation timed out", True
    except Exception as exc:
        return -1, "", f"Validator execution error: {exc}", False


class BaseCodeValidator(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult: ...


class PythonValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "python-ast"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        try:
            ast.parse(source)
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
                tool_version=f"Python {sys.version.split()[0]}",
            )
        except SyntaxError as exc:
            duration = (time.monotonic() - start) * 1000
            diag = CodeDiagnostic(
                line=exc.lineno,
                column=exc.offset,
                message=exc.msg or "Python syntax error",
                severity="error",
            )
            return ValidationResult(
                status=ValidationStatus.INVALID,
                validator=self.name,
                language=language,
                diagnostics=[diag],
                parse_success=False,
                duration_ms=round(duration, 2),
                tool_version=f"Python {sys.version.split()[0]}",
            )
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.ERROR,
                validator=self.name,
                language=language,
                diagnostics=[CodeDiagnostic(message=f"AST parse error: {exc}")],
                duration_ms=round(duration, 2),
            )


class JsonValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "json-parser"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        try:
            json.loads(source)
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
            )
        except json.JSONDecodeError as exc:
            duration = (time.monotonic() - start) * 1000
            diag = CodeDiagnostic(
                line=exc.lineno,
                column=exc.colno,
                message=exc.msg,
                severity="error",
            )
            return ValidationResult(
                status=ValidationStatus.INVALID,
                validator=self.name,
                language=language,
                diagnostics=[diag],
                parse_success=False,
                duration_ms=round(duration, 2),
            )


class YamlValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "yaml-parser"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        try:
            yaml.safe_load(source)
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
            )
        except yaml.YAMLError as exc:
            duration = (time.monotonic() - start) * 1000
            line = None
            col = None
            if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
                line = exc.problem_mark.line + 1
                col = exc.problem_mark.column + 1
            diag = CodeDiagnostic(
                line=line,
                column=col,
                message=str(exc),
                severity="error",
            )
            return ValidationResult(
                status=ValidationStatus.INVALID,
                validator=self.name,
                language=language,
                diagnostics=[diag],
                parse_success=False,
                duration_ms=round(duration, 2),
            )


class TomlValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "toml-parser"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        try:
            tomllib.loads(source)
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
            )
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.INVALID,
                validator=self.name,
                language=language,
                diagnostics=[CodeDiagnostic(message=str(exc))],
                parse_success=False,
                duration_ms=round(duration, 2),
            )


class XmlValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "xml-parser"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        try:
            defusedxml.minidom.parseString(source)
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
            )
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.INVALID,
                validator=self.name,
                language=language,
                diagnostics=[CodeDiagnostic(message=f"XML parse error: {exc}")],
                parse_success=False,
                duration_ms=round(duration, 2),
            )


class HtmlValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "html-parser"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()

        class RobustHtmlParser(html.parser.HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.errors: list[str] = []

            def error(self, message: str) -> None:
                self.errors.append(message)

        parser = RobustHtmlParser()
        try:
            parser.feed(source)
            duration = (time.monotonic() - start) * 1000
            if parser.errors:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    validator=self.name,
                    language=language,
                    diagnostics=[CodeDiagnostic(message=err) for err in parser.errors],
                    parse_success=False,
                    duration_ms=round(duration, 2),
                )
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
            )
        except Exception as exc:
            duration = (time.monotonic() - start) * 1000
            return ValidationResult(
                status=ValidationStatus.INVALID,
                validator=self.name,
                language=language,
                diagnostics=[CodeDiagnostic(message=str(exc))],
                parse_success=False,
                duration_ms=round(duration, 2),
            )


class BashValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "bash-syntax-check"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        bash_path = shutil.which("bash")
        if not bash_path:
            return ValidationResult(
                status=ValidationStatus.TOOL_UNAVAILABLE,
                validator=self.name,
                language=language,
                skipped_reason="bash toolchain not available on local PATH",
                duration_ms=0.0,
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_file = tmp_path / "check.sh"
            script_file.write_text(source, encoding="utf-8")

            ret, stdout, stderr, timed_out = run_safe_validator_subprocess(
                [bash_path, "-n", str(script_file)],
                temp_dir=tmp_path,
                timeout=2.0,
            )

        duration = (time.monotonic() - start) * 1000

        if timed_out:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                validator=self.name,
                language=language,
                diagnostics=[CodeDiagnostic(message="Bash syntax check timed out")],
                duration_ms=round(duration, 2),
            )

        if ret == 0:
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                parse_success=True,
                duration_ms=round(duration, 2),
                tool_version="bash -n",
            )

        err_msg = stderr.strip() or stdout.strip() or "Bash syntax error"
        return ValidationResult(
            status=ValidationStatus.INVALID,
            validator=self.name,
            language=language,
            diagnostics=[CodeDiagnostic(message=err_msg)],
            parse_success=False,
            duration_ms=round(duration, 2),
            tool_version="bash -n",
        )


class CppValidator(BaseCodeValidator):
    @property
    def name(self) -> str:
        return "cpp-compiler-check"

    async def validate(
        self, source: str, language: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        start = time.monotonic()
        compiler = shutil.which("g++") or shutil.which("clang++") or shutil.which("gcc")
        if not compiler:
            return ValidationResult(
                status=ValidationStatus.TOOL_UNAVAILABLE,
                validator=self.name,
                language=language,
                skipped_reason="No C/C++ compiler (g++, clang++, gcc) found on local PATH",
                duration_ms=0.0,
            )

        lang_flag = "-x c" if language == "c" else "-x c++"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source_file = tmp_path / "check.cpp"
            source_file.write_text(source, encoding="utf-8")

            ret, stdout, stderr, timed_out = run_safe_validator_subprocess(
                [compiler, "-fsyntax-only", lang_flag, str(source_file)],
                temp_dir=tmp_path,
                timeout=3.0,
            )

        duration = (time.monotonic() - start) * 1000

        if timed_out:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                validator=self.name,
                language=language,
                diagnostics=[CodeDiagnostic(message="C/C++ syntax check timed out")],
                duration_ms=round(duration, 2),
            )

        if ret == 0:
            return ValidationResult(
                status=ValidationStatus.VALID,
                validator=self.name,
                language=language,
                compile_success=True,
                duration_ms=round(duration, 2),
                tool_version=Path(compiler).name,
            )

        err_msg = stderr.strip() or stdout.strip() or "C/C++ compilation error"
        return ValidationResult(
            status=ValidationStatus.INVALID,
            validator=self.name,
            language=language,
            diagnostics=[CodeDiagnostic(message=err_msg)],
            compile_success=False,
            duration_ms=round(duration, 2),
            tool_version=Path(compiler).name,
        )


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: dict[str, BaseCodeValidator] = {
            "python": PythonValidator(),
            "json": JsonValidator(),
            "yaml": YamlValidator(),
            "toml": TomlValidator(),
            "xml": XmlValidator(),
            "html": HtmlValidator(),
            "bash": BashValidator(),
            "c": CppValidator(),
            "cpp": CppValidator(),
        }

    def register(self, language_id: str, validator: BaseCodeValidator) -> None:
        self._validators[language_id] = validator

    def get_validator(self, language_id: str) -> BaseCodeValidator | None:
        normalized = normalize_language_label(language_id)
        return self._validators.get(normalized)

    async def validate(
        self, source: str, raw_language_label: str, context: dict[str, Any] | None = None
    ) -> ValidationResult:
        normalized_lang = normalize_language_label(raw_language_label)
        validator = self.get_validator(normalized_lang)

        if not validator:
            return ValidationResult(
                status=ValidationStatus.UNSUPPORTED,
                validator="none",
                language=normalized_lang,
                skipped_reason=f"No validator configured for language '{normalized_lang}'",
            )

        try:
            return await validator.validate(source, normalized_lang, context)
        except Exception as exc:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                validator=validator.name,
                language=normalized_lang,
                diagnostics=[CodeDiagnostic(message=f"Validator internal error: {exc}")],
            )


_DEFAULT_VALIDATOR_REGISTRY = ValidatorRegistry()


def get_validator_registry() -> ValidatorRegistry:
    return _DEFAULT_VALIDATOR_REGISTRY
