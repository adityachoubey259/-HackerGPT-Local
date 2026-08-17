from __future__ import annotations

import ast
import json
import re


def extract_fenced_code(markdown: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).strip(), match.group(2))
        for match in re.finditer(r"^```([^\n`]*)\n([\s\S]*?)\n```$", markdown, re.MULTILINE)
    ]


def fenced(language: str, code: str) -> str:
    return f"```{language}\n{code}\n```"


CPP = "\n".join(
    [
        "#include <iostream>",
        "#include <vector>",
        "#include <string>",
        "",
        "int main() {",
        '    std::vector<std::string> values{"a", "b"};',
        "",
        "    for (const auto& value : values) {",
        "        std::cout << value << '*' << '\\n';",
        "    }",
        "",
        "    return 0;",
        "}",
    ]
)

PYTHON = "\n".join(
    [
        "from my_package.api_models import HealthResponse",
        "",
        "",
        "def health_check() -> HealthResponse:",
        "    status_code = 200",
        "    return HealthResponse(",
        '        status="healthy",',
        "        status_code=status_code,",
        "    )",
    ]
)

BASH = "\n".join(
    [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "printf '%s\\n' \"$HOME\"",
        'find . -type f -name "*.py"',
    ]
)

POWERSHELL = "\n".join(
    [
        '$root = "C:\\Projects\\HackerGPT Local"',
        'Get-ChildItem -Path $root -Filter "*.py"',
        'Write-Host "$($LASTEXITCODE)"',
    ]
)

JSON_SOURCE = json.dumps(
    {
        "agent_id": "expert",
        "response_mode": "direct_expert",
        "features": ["rag", "memory", "tools"],
    },
    indent=2,
)

HTML = "\n".join(
    [
        "<!doctype html>",
        '<html lang="en">',
        "  <body>",
        '    <main id="app">',
        '      <button type="button">Run & Verify</button>',
        "    </main>",
        "  </body>",
        "</html>",
    ]
)

SQL = "\n".join(
    [
        "SELECT",
        "    user_id,",
        "    COUNT(*) AS request_count",
        "FROM request_logs",
        "WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'",
        "GROUP BY user_id;",
    ]
)

MARKDOWN = "\n".join(
    [
        "# Build Notes",
        "",
        "Use `npm.cmd run build`.",
        "",
        "- Keep `_underscores_`",
        "- Keep `*asterisks*`",
        "- Keep `<tags>` when intentionally written",
    ]
)


def test_fenced_code_fixture_extraction_preserves_literal_source() -> None:
    fixtures = {
        "cpp": CPP,
        "python": PYTHON,
        "bash": BASH,
        "powershell": POWERSHELL,
        "json": JSON_SOURCE,
        "html": HTML,
        "sql": SQL,
        "markdown": MARKDOWN,
    }

    for language, code in fixtures.items():
        assert extract_fenced_code(fenced(language, code)) == [(language, code)]
        escaped_markdown_tokens = ("\\#", "\\<", "\\>", "\\*", "\\_")
        assert not any(token in code for token in escaped_markdown_tokens)


def test_python_fixture_remains_ast_parseable() -> None:
    [(_, code)] = extract_fenced_code(fenced("python", PYTHON))

    ast.parse(code)
    assert "my_package" in code
    assert "api_models" in code
    assert "status_code" in code


def test_json_fixture_remains_json_parseable() -> None:
    [(_, code)] = extract_fenced_code(fenced("json", JSON_SOURCE))

    parsed = json.loads(code)
    assert parsed["agent_id"] == "expert"
    assert parsed["response_mode"] == "direct_expert"


def test_language_labels_preserve_unknown_source() -> None:
    labels = [
        "cpp",
        "python",
        "bash",
        "powershell",
        "json",
        "html",
        "sql",
        "markdown",
        "typescript",
        "javascript",
        "rust",
        "go",
        "java",
        "csharp",
        "unknownlang",
    ]
    source = "alpha_beta * <tag> $HOME"

    for label in labels:
        assert extract_fenced_code(fenced(label, source)) == [(label, source)]
