"""Linux and Kali Linux expert assistant service."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LinuxCommandRecommendation(BaseModel):
    target_os: str = "Kali Linux"
    command: str
    flags_explanation: list[str] = Field(default_factory=list)
    expected_output: str
    troubleshooting: list[str] = Field(default_factory=list)


LINUX_SYSTEM_PROMPT = """You are the HackerGPT Local Linux & Kali Linux Assistant.
Your specialization is expert Linux administration, systems engineering, Kali Linux tools,
shell scripting, networking, and security lab workflows.

Rules:
1. Answer directly and concisely.
2. Provide exact syntax for Linux and Kali Linux commands.
3. Highlight critical flags and explain expected output clearly.
4. Distinguish root/sudo vs user privileges.
5. Provide actionable troubleshooting steps for failures.
"""


def format_linux_command_response(
    command: str,
    *,
    target_os: str = "Kali Linux",
    flags: list[str] | None = None,
    expected: str = "Successful execution with clean status code.",
    troubleshooting: list[str] | None = None,
) -> str:
    flags_str = "\n".join(f"- {f}" for f in flags) if flags else "- Standard execution flags"
    tb_list = troubleshooting or ["Check file permissions and network interface status."]
    tb_str = "\n".join(f"- {t}" for t in tb_list)

    return f"""Run on:
{target_os}

Command:
```bash
{command}
```

Important flags:
{flags_str}

Expected:
{expected}

If it fails:
{tb_str}"""
