"""Centralized, declarative multi-language registry for HackerGPT Local.

Provides language label normalization, capabilities, and family metadata across
programming, scripting, markup, configuration, database, infrastructure,
low-level, GPU, smart contract, and build languages.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LanguageFamily(StrEnum):
    GENERAL = "general"
    FUNCTIONAL = "functional"
    SHELL = "shell"
    WEB = "web"
    DATA = "data"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    LOW_LEVEL = "low_level"
    GPU = "gpu"
    SMART_CONTRACT = "smart_contract"
    BUILD = "build"
    OTHER = "other"


class LanguageDefinition(BaseModel):
    id: str
    aliases: list[str] = Field(default_factory=list)
    display_name: str
    family: LanguageFamily = LanguageFamily.OTHER
    file_extensions: list[str] = Field(default_factory=list)
    validator_id: str | None = None
    syntax_highlighter_id: str | None = None
    executable_validation_allowed: bool = False
    compile_only_supported: bool = False
    parser_supported: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


_BUILTIN_LANGUAGES: list[LanguageDefinition] = [
    # General Programming
    LanguageDefinition(
        id="python",
        aliases=["py", "python3", "pyw"],
        display_name="Python",
        family=LanguageFamily.GENERAL,
        file_extensions=[".py", ".pyi"],
        validator_id="python",
        syntax_highlighter_id="python",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="javascript",
        aliases=["js", "node", "cjs", "mjs"],
        display_name="JavaScript",
        family=LanguageFamily.GENERAL,
        file_extensions=[".js", ".cjs", ".mjs"],
        validator_id="javascript",
        syntax_highlighter_id="javascript",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="typescript",
        aliases=["ts"],
        display_name="TypeScript",
        family=LanguageFamily.GENERAL,
        file_extensions=[".ts", ".cts", ".mts"],
        validator_id="typescript",
        syntax_highlighter_id="typescript",
        compile_only_supported=True,
        parser_supported=True,
    ),
    LanguageDefinition(
        id="javascriptreact",
        aliases=["jsx"],
        display_name="JavaScript (JSX)",
        family=LanguageFamily.GENERAL,
        file_extensions=[".jsx"],
        validator_id="javascript",
        syntax_highlighter_id="jsx",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="typescriptreact",
        aliases=["tsx"],
        display_name="TypeScript (TSX)",
        family=LanguageFamily.GENERAL,
        file_extensions=[".tsx"],
        validator_id="typescript",
        syntax_highlighter_id="tsx",
        compile_only_supported=True,
        parser_supported=True,
    ),
    LanguageDefinition(
        id="java",
        aliases=["jav"],
        display_name="Java",
        family=LanguageFamily.GENERAL,
        file_extensions=[".java"],
        validator_id="java",
        syntax_highlighter_id="java",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="kotlin",
        aliases=["kt", "kts"],
        display_name="Kotlin",
        family=LanguageFamily.GENERAL,
        file_extensions=[".kt", ".kts"],
        validator_id="kotlin",
        syntax_highlighter_id="kotlin",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="scala",
        aliases=["sc"],
        display_name="Scala",
        family=LanguageFamily.GENERAL,
        file_extensions=[".scala", ".sc"],
        validator_id="scala",
        syntax_highlighter_id="scala",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="c",
        aliases=[],
        display_name="C",
        family=LanguageFamily.GENERAL,
        file_extensions=[".c", ".h"],
        validator_id="c",
        syntax_highlighter_id="c",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="cpp",
        aliases=["c++", "cxx", "cc", "hpp", "hxx", "h++"],
        display_name="C++",
        family=LanguageFamily.GENERAL,
        file_extensions=[".cpp", ".hpp", ".cc", ".cxx"],
        validator_id="cpp",
        syntax_highlighter_id="cpp",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="csharp",
        aliases=["cs", "c#"],
        display_name="C#",
        family=LanguageFamily.GENERAL,
        file_extensions=[".cs"],
        validator_id="csharp",
        syntax_highlighter_id="csharp",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="go",
        aliases=["golang"],
        display_name="Go",
        family=LanguageFamily.GENERAL,
        file_extensions=[".go"],
        validator_id="go",
        syntax_highlighter_id="go",
        compile_only_supported=True,
        parser_supported=True,
    ),
    LanguageDefinition(
        id="rust",
        aliases=["rs"],
        display_name="Rust",
        family=LanguageFamily.GENERAL,
        file_extensions=[".rs"],
        validator_id="rust",
        syntax_highlighter_id="rust",
        compile_only_supported=True,
        parser_supported=True,
    ),
    LanguageDefinition(
        id="swift",
        aliases=[],
        display_name="Swift",
        family=LanguageFamily.GENERAL,
        file_extensions=[".swift"],
        validator_id="swift",
        syntax_highlighter_id="swift",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="objectivec",
        aliases=["objc", "obj-c", "m"],
        display_name="Objective-C",
        family=LanguageFamily.GENERAL,
        file_extensions=[".m", ".h"],
        validator_id="objectivec",
        syntax_highlighter_id="objectivec",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="dart",
        aliases=[],
        display_name="Dart",
        family=LanguageFamily.GENERAL,
        file_extensions=[".dart"],
        validator_id="dart",
        syntax_highlighter_id="dart",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="ruby",
        aliases=["rb"],
        display_name="Ruby",
        family=LanguageFamily.GENERAL,
        file_extensions=[".rb"],
        validator_id="ruby",
        syntax_highlighter_id="ruby",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="php",
        aliases=["php3", "php4", "php5", "phtml"],
        display_name="PHP",
        family=LanguageFamily.GENERAL,
        file_extensions=[".php"],
        validator_id="php",
        syntax_highlighter_id="php",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="perl",
        aliases=["pl", "pm"],
        display_name="Perl",
        family=LanguageFamily.GENERAL,
        file_extensions=[".pl", ".pm"],
        validator_id="perl",
        syntax_highlighter_id="perl",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="lua",
        aliases=[],
        display_name="Lua",
        family=LanguageFamily.GENERAL,
        file_extensions=[".lua"],
        validator_id="lua",
        syntax_highlighter_id="lua",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="julia",
        aliases=["jl"],
        display_name="Julia",
        family=LanguageFamily.GENERAL,
        file_extensions=[".jl"],
        validator_id="julia",
        syntax_highlighter_id="julia",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="r",
        aliases=["rscript"],
        display_name="R",
        family=LanguageFamily.GENERAL,
        file_extensions=[".r", ".R"],
        validator_id="r",
        syntax_highlighter_id="r",
        parser_supported=True,
    ),
    # Functional
    LanguageDefinition(
        id="haskell",
        aliases=["hs"],
        display_name="Haskell",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".hs", ".lhs"],
        validator_id="haskell",
        syntax_highlighter_id="haskell",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="ocaml",
        aliases=["ml"],
        display_name="OCaml",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".ml", ".mli"],
        validator_id="ocaml",
        syntax_highlighter_id="ocaml",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="fsharp",
        aliases=["fs", "f#"],
        display_name="F#",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".fs", ".fsi", ".fsx"],
        validator_id="fsharp",
        syntax_highlighter_id="fsharp",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="elixir",
        aliases=["ex", "exs"],
        display_name="Elixir",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".ex", ".exs"],
        validator_id="elixir",
        syntax_highlighter_id="elixir",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="erlang",
        aliases=["erl", "hrl"],
        display_name="Erlang",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".erl", ".hrl"],
        validator_id="erlang",
        syntax_highlighter_id="erlang",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="clojure",
        aliases=["clj", "cljs"],
        display_name="Clojure",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".clj", ".cljs", ".edn"],
        validator_id="clojure",
        syntax_highlighter_id="clojure",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="lisp",
        aliases=["scheme", "elisp", "scm", "lisp"],
        display_name="Lisp / Scheme",
        family=LanguageFamily.FUNCTIONAL,
        file_extensions=[".lisp", ".scm", ".el"],
        validator_id="lisp",
        syntax_highlighter_id="lisp",
        parser_supported=True,
    ),
    # Shell / System
    LanguageDefinition(
        id="bash",
        aliases=["sh", "shell", "zsh", "posix"],
        display_name="Bash / Shell",
        family=LanguageFamily.SHELL,
        file_extensions=[".sh", ".bash", ".zsh"],
        validator_id="bash",
        syntax_highlighter_id="bash",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="fish",
        aliases=[],
        display_name="Fish Shell",
        family=LanguageFamily.SHELL,
        file_extensions=[".fish"],
        validator_id="fish",
        syntax_highlighter_id="fish",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="powershell",
        aliases=["ps1", "psm1", "psd1", "pwsh"],
        display_name="PowerShell",
        family=LanguageFamily.SHELL,
        file_extensions=[".ps1", ".psm1", ".psd1"],
        validator_id="powershell",
        syntax_highlighter_id="powershell",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="batch",
        aliases=["bat", "cmd"],
        display_name="Windows Batch",
        family=LanguageFamily.SHELL,
        file_extensions=[".bat", ".cmd"],
        validator_id="batch",
        syntax_highlighter_id="batch",
        parser_supported=True,
    ),
    # Web / Markup
    LanguageDefinition(
        id="html",
        aliases=["xhtml"],
        display_name="HTML",
        family=LanguageFamily.WEB,
        file_extensions=[".html", ".htm"],
        validator_id="html",
        syntax_highlighter_id="html",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="css",
        aliases=[],
        display_name="CSS",
        family=LanguageFamily.WEB,
        file_extensions=[".css"],
        validator_id="css",
        syntax_highlighter_id="css",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="scss",
        aliases=["sass", "less"],
        display_name="SCSS / Sass / Less",
        family=LanguageFamily.WEB,
        file_extensions=[".scss", ".sass", ".less"],
        validator_id="scss",
        syntax_highlighter_id="scss",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="xml",
        aliases=["svg"],
        display_name="XML / SVG",
        family=LanguageFamily.WEB,
        file_extensions=[".xml", ".svg"],
        validator_id="xml",
        syntax_highlighter_id="xml",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="markdown",
        aliases=["md", "mdown"],
        display_name="Markdown",
        family=LanguageFamily.WEB,
        file_extensions=[".md", ".markdown"],
        validator_id="markdown",
        syntax_highlighter_id="markdown",
        parser_supported=True,
    ),
    # Data / Config
    LanguageDefinition(
        id="json",
        aliases=["jsonc"],
        display_name="JSON",
        family=LanguageFamily.DATA,
        file_extensions=[".json"],
        validator_id="json",
        syntax_highlighter_id="json",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="json5",
        aliases=[],
        display_name="JSON5",
        family=LanguageFamily.DATA,
        file_extensions=[".json5"],
        validator_id="json5",
        syntax_highlighter_id="json",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="yaml",
        aliases=["yml"],
        display_name="YAML",
        family=LanguageFamily.DATA,
        file_extensions=[".yaml", ".yml"],
        validator_id="yaml",
        syntax_highlighter_id="yaml",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="toml",
        aliases=[],
        display_name="TOML",
        family=LanguageFamily.DATA,
        file_extensions=[".toml"],
        validator_id="toml",
        syntax_highlighter_id="toml",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="ini",
        aliases=["dotenv", "env"],
        display_name="INI / dotenv",
        family=LanguageFamily.DATA,
        file_extensions=[".ini", ".env"],
        validator_id="ini",
        syntax_highlighter_id="ini",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="csv",
        aliases=[],
        display_name="CSV",
        family=LanguageFamily.DATA,
        file_extensions=[".csv"],
        validator_id="csv",
        syntax_highlighter_id="csv",
        parser_supported=True,
    ),
    # Databases / Query
    LanguageDefinition(
        id="sql",
        aliases=[
            "postgresql",
            "postgres",
            "mysql",
            "sqlite",
            "tsql",
            "t-sql",
            "plsql",
            "pl/sql",
        ],
        display_name="SQL",
        family=LanguageFamily.DATABASE,
        file_extensions=[".sql"],
        validator_id="sql",
        syntax_highlighter_id="sql",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="graphql",
        aliases=["gql"],
        display_name="GraphQL",
        family=LanguageFamily.DATABASE,
        file_extensions=[".graphql", ".gql"],
        validator_id="graphql",
        syntax_highlighter_id="graphql",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="cypher",
        aliases=[],
        display_name="Cypher",
        family=LanguageFamily.DATABASE,
        file_extensions=[".cyp", ".cypher"],
        validator_id="cypher",
        syntax_highlighter_id="cypher",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="promql",
        aliases=[],
        display_name="PromQL",
        family=LanguageFamily.DATABASE,
        file_extensions=[".promql"],
        validator_id="promql",
        syntax_highlighter_id="promql",
        parser_supported=True,
    ),
    # Infrastructure
    LanguageDefinition(
        id="dockerfile",
        aliases=["docker"],
        display_name="Dockerfile",
        family=LanguageFamily.INFRASTRUCTURE,
        file_extensions=["Dockerfile", ".dockerfile"],
        validator_id="dockerfile",
        syntax_highlighter_id="docker",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="terraform",
        aliases=["hcl", "tf"],
        display_name="Terraform / HCL",
        family=LanguageFamily.INFRASTRUCTURE,
        file_extensions=[".tf", ".hcl"],
        validator_id="terraform",
        syntax_highlighter_id="hcl",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="nginx",
        aliases=[],
        display_name="Nginx Config",
        family=LanguageFamily.INFRASTRUCTURE,
        file_extensions=[".nginx", ".conf"],
        validator_id="nginx",
        syntax_highlighter_id="nginx",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="apache",
        aliases=["apacheconf"],
        display_name="Apache Config",
        family=LanguageFamily.INFRASTRUCTURE,
        file_extensions=[".htaccess"],
        validator_id="apache",
        syntax_highlighter_id="apacheconf",
        parser_supported=True,
    ),
    # Low-Level
    LanguageDefinition(
        id="assembly",
        aliases=["asm", "s", "x86", "x86_64", "x86-64", "arm", "arm64"],
        display_name="Assembly",
        family=LanguageFamily.LOW_LEVEL,
        file_extensions=[".asm", ".s", ".S"],
        validator_id="assembly",
        syntax_highlighter_id="nasm",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="wasm",
        aliases=["wat"],
        display_name="WebAssembly Text",
        family=LanguageFamily.LOW_LEVEL,
        file_extensions=[".wat", ".wasm"],
        validator_id="wasm",
        syntax_highlighter_id="wasm",
        parser_supported=True,
    ),
    # GPU / Scientific
    LanguageDefinition(
        id="cuda",
        aliases=["cu", "cuh"],
        display_name="CUDA C/C++",
        family=LanguageFamily.GPU,
        file_extensions=[".cu", ".cuh"],
        validator_id="cuda",
        syntax_highlighter_id="cpp",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="opencl",
        aliases=["cl"],
        display_name="OpenCL C",
        family=LanguageFamily.GPU,
        file_extensions=[".cl"],
        validator_id="opencl",
        syntax_highlighter_id="c",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="glsl",
        aliases=["vert", "frag"],
        display_name="GLSL",
        family=LanguageFamily.GPU,
        file_extensions=[".glsl", ".vert", ".frag"],
        validator_id="glsl",
        syntax_highlighter_id="glsl",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="hlsl",
        aliases=[],
        display_name="HLSL",
        family=LanguageFamily.GPU,
        file_extensions=[".hlsl"],
        validator_id="hlsl",
        syntax_highlighter_id="hlsl",
        compile_only_supported=True,
    ),
    # Smart Contracts
    LanguageDefinition(
        id="solidity",
        aliases=["sol"],
        display_name="Solidity",
        family=LanguageFamily.SMART_CONTRACT,
        file_extensions=[".sol"],
        validator_id="solidity",
        syntax_highlighter_id="solidity",
        compile_only_supported=True,
    ),
    LanguageDefinition(
        id="vyper",
        aliases=["vy"],
        display_name="Vyper",
        family=LanguageFamily.SMART_CONTRACT,
        file_extensions=[".vy"],
        validator_id="vyper",
        syntax_highlighter_id="python",
        compile_only_supported=True,
    ),
    # Build / Tooling
    LanguageDefinition(
        id="make",
        aliases=["makefile", "mk"],
        display_name="Makefile",
        family=LanguageFamily.BUILD,
        file_extensions=["Makefile", ".mk"],
        validator_id="make",
        syntax_highlighter_id="makefile",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="cmake",
        aliases=[],
        display_name="CMake",
        family=LanguageFamily.BUILD,
        file_extensions=["CMakeLists.txt", ".cmake"],
        validator_id="cmake",
        syntax_highlighter_id="cmake",
        parser_supported=True,
    ),
    LanguageDefinition(
        id="meson",
        aliases=[],
        display_name="Meson",
        family=LanguageFamily.BUILD,
        file_extensions=["meson.build"],
        validator_id="meson",
        syntax_highlighter_id="meson",
        parser_supported=True,
    ),
]


class LanguageRegistry:
    """Centralized multi-language registry."""

    def __init__(self, custom_languages: list[LanguageDefinition] | None = None) -> None:
        self._languages: dict[str, LanguageDefinition] = {}
        self._alias_map: dict[str, str] = {}

        for lang in _BUILTIN_LANGUAGES:
            self.register(lang)

        if custom_languages:
            for lang in custom_languages:
                self.register(lang)

    def register(self, definition: LanguageDefinition) -> None:
        self._languages[definition.id] = definition
        self._alias_map[definition.id.lower()] = definition.id
        for alias in definition.aliases:
            self._alias_map[alias.lower()] = definition.id

    def normalize_label(self, label: str) -> str:
        cleaned = label.strip().lower()
        if not cleaned:
            return "text"
        return self._alias_map.get(cleaned, cleaned)

    def get(self, label: str) -> LanguageDefinition:
        normalized_id = self.normalize_label(label)
        if normalized_id in self._languages:
            return self._languages[normalized_id]

        cleaned_label = label.strip() or "text"
        return LanguageDefinition(
            id=normalized_id,
            aliases=[],
            display_name=cleaned_label,
            family=LanguageFamily.OTHER,
            file_extensions=[],
            validator_id=None,
            syntax_highlighter_id=normalized_id,
            executable_validation_allowed=False,
            compile_only_supported=False,
            parser_supported=False,
        )


_DEFAULT_REGISTRY = LanguageRegistry()


def get_language_registry() -> LanguageRegistry:
    return _DEFAULT_REGISTRY


def normalize_language_label(label: str) -> str:
    return _DEFAULT_REGISTRY.normalize_label(label)
