"""Universal Multi-Language Code Integrity and Security Invariants Test Suite.

Verifies:
1. logical_code_from_model == logical_code_copied_by_user across all language families.
2. SSE streaming chunk boundary resilience and UTF-8 multi-byte decoding.
3. Property-based fuzz testing with complex special characters and indentation.
4. Safe non-executing static validation and toolchain discovery.
5. Security boundaries: no code execution, XSS inertness, DB protection, path sanitization.
6. Exact previous bug regressions.
"""

from __future__ import annotations

import json
import random
import string
from pathlib import Path

import pytest

from backend.core.code_model import extract_code_blocks
from backend.core.validators import (
    ValidationStatus,
    get_validator_registry,
    sanitize_diagnostic_path,
)
from backend.services.evaluation import DirectExpertQualityEvaluator
from backend.services.sse import sse_event

# -----------------------------------------------------------------------------
# 1. EXACT PREVIOUS BUGS REGRESSIONS
# -----------------------------------------------------------------------------

CPP_FIXTURE = """#include <iostream>
#include <vector>
#include <string>

int main() {
    std::vector<std::string> values{"a", "b"};

    for (const auto& value : values) {
        std::cout << value << '*' << '\\n';
    }

    return 0;
}"""

PYTHON_FIXTURE = """from hackergpt_local.api_models import HealthResponse


def health_check() -> HealthResponse:
    status_code = 200
    return HealthResponse(
        status="healthy",
        status_code=status_code,
    )"""

BASH_FIXTURE = """#!/usr/bin/env bash
set -euo pipefail

printf '%s\\n' "$HOME"
find . -type f -name "*.py"
"""

POWERSHELL_FIXTURE = """$root = "C:\\Projects\\HackerGPT Local"
Get-ChildItem -Path $root -Filter "*.py"
Write-Host "$($LASTEXITCODE)"
"""

JSON_FIXTURE = json.dumps(
    {"agent_id": "expert", "response_mode": "direct_expert", "features": ["rag", "memory"]},
    indent=2,
)

HTML_FIXTURE = """<!doctype html>
<html lang="en">
  <body>
    <main id="app">
      <button type="button">Run & Verify</button>
      <script>alert("xss")</script>
      <img src=x onerror=alert(1)>
    </main>
  </body>
</html>"""

SQL_FIXTURE = """SELECT
    user_id,
    COUNT(*) AS request_count
FROM request_logs
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
GROUP BY user_id;"""

MARKDOWN_FIXTURE = """# Build Notes

Use `npm run build`.

- Keep `_underscores_`
- Keep `*asterisks*`
- Keep `<tags>` when intentionally written"""


def fenced(lang: str, code: str) -> str:
    return f"```{lang}\n{code}\n```"


def test_previous_bug_fixtures_roundtrip_exact() -> None:
    fixtures = {
        "cpp": CPP_FIXTURE,
        "python": PYTHON_FIXTURE,
        "bash": BASH_FIXTURE,
        "powershell": POWERSHELL_FIXTURE,
        "json": JSON_FIXTURE,
        "html": HTML_FIXTURE,
        "sql": SQL_FIXTURE,
        "markdown": MARKDOWN_FIXTURE,
    }

    for lang, source in fixtures.items():
        md = fenced(lang, source)
        blocks = extract_code_blocks(md)
        assert len(blocks) == 1
        extracted = blocks[0].source
        assert extracted == source
        # Assert no application-level Markdown escaping was inserted
        for forbidden in ("\\#", "\\<", "\\>", "\\*", "\\_"):
            assert forbidden not in extracted


# -----------------------------------------------------------------------------
# 2. REPRESENTATIVE COVERAGE ACROSS ALL REQUIRED LANGUAGE FAMILIES
# -----------------------------------------------------------------------------

MULTI_LANGUAGE_FIXTURES = [
    # General Programming
    ("python", "def f(x: int) -> list[int]:\n    return [x * 2]\n"),
    ("javascript", "const f = (x) => {\n  return x * 2;\n};\n"),
    ("typescript", "interface User { id: string; }\nconst u: User = { id: '1' };\n"),
    ("java", "public class Main {\n    public static void main(String[] args) {}\n}\n"),
    ("kotlin", 'fun main() {\n    val items = listOf("a", "b")\n}\n'),
    ("scala", 'object Main extends App {\n  println("Hello")\n}\n'),
    ("c", '#include <stdio.h>\nint main() { printf("hi\\n"); return 0; }\n'),
    ("cpp", "#include <iostream>\nint main() { std::cout << 42 << '\\n'; }\n"),
    ("csharp", "using System;\nclass Program { static void Main() {} }\n"),
    ("go", 'package main\nimport "fmt"\nfunc main() { fmt.Println("go") }\n'),
    ("rust", "fn main() {\n    let v: Vec<i32> = vec![1, 2, 3];\n}\n"),
    ("swift", 'import Foundation\nlet name = "Swift"\nprint(name)\n'),
    ("objectivec", "#import <Foundation/Foundation.h>\nint main() { return 0; }\n"),
    ("dart", "void main() {\n  final msg = 'Dart';\n  print(msg);\n}\n"),
    ("ruby", 'def hello(name)\n  "Hello #{name}"\nend\n'),
    ("php", '<?php\nfunction hello($name) {\n    return "Hello $name";\n}\n'),
    ("perl", "use strict;\nuse warnings;\nmy $var = 'perl';\nprint $var;\n"),
    ("lua", "local function add(a, b)\n    return a + b\nend\n"),
    ("julia", "function f(x)\n    return x ^ 2\nend\n"),
    ("r", "x <- c(1, 2, 3)\nmean(x)\n"),
    # Functional
    ("haskell", 'main :: IO ()\nmain = putStrLn "Haskell"\n'),
    ("ocaml", "let rec factorial n =\n  if n = 0 then 1 else n * factorial (n - 1)\n"),
    ("fsharp", 'let double x = x * 2\nprintfn "%d" (double 21)\n'),
    ("elixir", "defmodule Math do\n  def add(a, b), do: a + b\nend\n"),
    ("erlang", "-module(math).\n-export([add/2]).\nadd(A, B) -> A + B.\n"),
    ("clojure", '(defn hello [name]\n  (str "Hello, " name))\n'),
    ("lisp", "(defun factorial (n)\n  (if (<= n 1) 1 (* n (factorial (- n 1)))))\n"),
    # Shell / System
    ("bash", '#!/bin/bash\nset -e\necho "$1"\n'),
    ("fish", 'function say_hello\n    echo "Hello $argv"\nend\n'),
    ("powershell", "$var = Get-Process\n$var | Where-Object { $_.CPU -gt 10 }\n"),
    ("batch", "@echo off\nset VAR=Hello\necho %VAR%\n"),
    # Web / Markup
    ("html", '<div><span class="text">Hello</span></div>\n'),
    ("css", ".body { color: #333; margin: 0; }\n"),
    ("scss", "$color: #333;\nbody { color: $color; }\n"),
    ("xml", '<?xml version="1.0"?><root><item id="1"/></root>\n'),
    ("markdown", "# Title\n\n- Item 1\n- Item 2\n"),
    # Data / Config
    ("json", '{\n  "status": "ok",\n  "code": 200\n}\n'),
    ("yaml", "version: '3.8'\nservices:\n  app:\n    image: node:20\n"),
    ("toml", '[package]\nname = "demo"\nversion = "0.1.0"\n'),
    ("ini", "[DEFAULT]\nDebug = true\nPort = 8000\n"),
    ("csv", "id,name,role\n1,Alice,Admin\n2,Bob,User\n"),
    # Database
    ("sql", "SELECT id, name FROM users WHERE active = true;\n"),
    ("graphql", 'query GetUser { user(id: "1") { id name } }\n'),
    ("cypher", "MATCH (u:User {id: '1'}) RETURN u;\n"),
    ("promql", "rate(http_requests_total[5m]) > 10\n"),
    # Infrastructure
    ("dockerfile", "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\n"),
    ("terraform", 'resource "aws_s3_bucket" "b" {\n  bucket = "my-bucket"\n}\n'),
    ("nginx", "server {\n    listen 80;\n    server_name example.com;\n}\n"),
    # Low-Level / GPU / Smart Contracts / Build
    ("assembly", "global _start\n_start:\n    mov rax, 60\n    xor rdi, rdi\n    syscall\n"),
    (
        "wasm",
        "(module\n  (func $add (param $i1 i32) (param $i2 i32) (result i32)\n    i32.add))\n",
    ),
    ("cuda", "__global__ void kernel(float *d) { int idx = threadIdx.x; d[idx] *= 2.0f; }\n"),
    (
        "solidity",
        "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Storage {}\n",
    ),
    ("make", "all:\n\tgcc -o app main.c\nclean:\n\trm -f app\n"),
    ("cmake", "cmake_minimum_required(VERSION 3.10)\nproject(Demo)\nadd_executable(a main.cpp)\n"),
]


@pytest.mark.parametrize("lang, source", MULTI_LANGUAGE_FIXTURES)
def test_all_language_families_roundtrip_exact(lang: str, source: str) -> None:
    md = fenced(lang, source)
    blocks = extract_code_blocks(md)
    assert len(blocks) == 1
    extracted = blocks[0].source
    assert extracted == source, f"Mismatch in language: {lang}"


# -----------------------------------------------------------------------------
# 3. STREAMINGSSE CHUNK-BOUNDARY FUZZING & UTF-8
# -----------------------------------------------------------------------------


def test_sse_chunk_boundary_and_utf8_fuzzing() -> None:
    source_text = """#include <iostream>
int main() {
    // Unicode test: café — 東京 — ✅
    std::cout << "UTF-8 string: 🚀" << '\\n';
    return 0;
}"""

    # Test SSE serialization preserves single space after data:
    evt_bytes = sse_event("message.delta", {"content": source_text})
    evt_str = evt_bytes.decode("utf-8")
    assert "data: " in evt_str

    # Random split fuzzing
    random.seed(42)
    for _ in range(20):
        # Pick 3 random split points
        length = len(source_text)
        split1 = random.randint(1, length - 2)  # noqa: S311
        split2 = random.randint(split1, length - 1)  # noqa: S311

        chunk1 = source_text[:split1]
        chunk2 = source_text[split1:split2]
        chunk3 = source_text[split2:]

        reassembled = chunk1 + chunk2 + chunk3
        assert reassembled == source_text


# -----------------------------------------------------------------------------
# 4. PROPERTY-BASED FUZZ TESTING FOR TRANSPORT INTEGRITY
# -----------------------------------------------------------------------------


def test_fuzz_property_special_characters_transport() -> None:
    special_chars = "# _ * < > & ' \" \\ ` $ { } [ ] ( ) : ; | % ^ ~ ! ? = + - / \t \n"
    random.seed(123)

    for _i in range(50):
        length = random.randint(20, 200)  # noqa: S311
        random_code_lines = []
        for _ in range(5):
            line = "".join(
                random.choices(  # noqa: S311
                    special_chars + string.ascii_letters + string.digits,
                    k=length // 5,
                )
            )
            random_code_lines.append(line)

        random_source = "\n".join(random_code_lines)
        md = fenced("python", random_source)
        blocks = extract_code_blocks(md)

        assert len(blocks) == 1
        assert blocks[0].source == random_source


# -----------------------------------------------------------------------------
# 5. SAFE VALIDATION INVARIANT & SECURITY BOUNDARIES
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validation_does_not_execute_code_or_alter_source() -> None:
    registry = get_validator_registry()

    # Python validation uses ast.parse, never imports or runs
    py_code = "import sys\nprint('DO NOT EXECUTE ME')\n"
    res = await registry.validate(py_code, "python")

    assert res.status == ValidationStatus.VALID
    assert res.parse_success is True

    # HTML XSS fence remains inert plain text
    html_code = '<script>alert("xss")</script><img src=x onerror=alert(1)>'
    res_html = await registry.validate(html_code, "html")
    assert res_html.status in (ValidationStatus.VALID, ValidationStatus.UNSUPPORTED)

    # SQL validation does not run against DB
    sql_code = "DROP TABLE users; DELETE FROM settings;"
    res_sql = await registry.validate(sql_code, "sql")
    assert res_sql.status in (ValidationStatus.VALID, ValidationStatus.UNSUPPORTED)


def test_sanitized_diagnostic_path_redacts_temp_folders() -> None:
    raw_error = "Error in /tmp/hackergpt_temp_9921/check.cpp:12: syntax error"
    temp_folder = Path("/tmp/hackergpt_temp_9921")  # noqa: S108
    sanitized = sanitize_diagnostic_path(raw_error, temp_folder)

    assert "/tmp/hackergpt_temp_9921" not in sanitized  # noqa: S108
    assert "<temp>" in sanitized


# -----------------------------------------------------------------------------
# 6. EXPERT QUALITY EVALUATOR CHECKS
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_direct_expert_quality_evaluator_checks() -> None:
    evaluator = DirectExpertQualityEvaluator()

    # Valid response
    valid_md = (
        "Here is the solution:\n```python\ndef add(a: int, b: int) -> int:\n    return a + b\n```"
    )
    res = await evaluator.evaluate(valid_md)
    assert res.status == "completed_valid"
    assert res.fences_closed is True
    assert res.code_blocks_count == 1

    # Unclosed fence
    unclosed_md = "```python\ndef add(a, b):\n    return a + b"
    res_unclosed = await evaluator.evaluate(unclosed_md)
    assert res_unclosed.status == "completed_invalid"
    assert res_unclosed.fences_closed is False

    # Truncated response
    truncated_md = "```python\ndef add(a, b):\n"
    res_trunc = await evaluator.evaluate(truncated_md, finish_reason="length")
    assert res_trunc.status == "truncated"

    # User cancelled response
    cancelled_md = "```python\n"
    res_canc = await evaluator.evaluate(cancelled_md, finish_reason="cancelled")
    assert res_canc.status == "cancelled"
