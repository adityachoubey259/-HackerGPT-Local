import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SecureMarkdown } from "./SecureMarkdown";
import { extractFencedCode, fencedMarkdown } from "../../test/markdownCode";
import { renderApp } from "../../test/testUtils";

const FIXTURES = [
  {
    language: "cpp",
    code: [
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
      "}"
    ].join("\n"),
    mustContain: [
      "#include <iostream>",
      "#include <vector>",
      "#include <string>",
      "std::vector<std::string>",
      "const auto& value",
      "<< '*'",
      "<< '\\n'"
    ]
  },
  {
    language: "python",
    code: [
      "from my_package.api_models import HealthResponse",
      "",
      "",
      "def health_check() -> HealthResponse:",
      "    status_code = 200",
      "    return HealthResponse(",
      '        status="healthy",',
      "        status_code=status_code,",
      "    )"
    ].join("\n"),
    mustContain: ["my_package", "api_models", "status_code"]
  },
  {
    language: "bash",
    code: [
      "#!/usr/bin/env bash",
      "set -euo pipefail",
      "",
      "printf '%s\\n' \"$HOME\"",
      'find . -type f -name "*.py"'
    ].join("\n"),
    mustContain: ["#!/usr/bin/env bash", "*.py", "$HOME"]
  },
  {
    language: "powershell",
    code: [
      '$root = "C:\\Projects\\HackerGPT Local"',
      'Get-ChildItem -Path $root -Filter "*.py"',
      'Write-Host "$($LASTEXITCODE)"'
    ].join("\n"),
    mustContain: ["$root", "*.py", "$($LASTEXITCODE)", "C:\\Projects\\HackerGPT Local"]
  },
  {
    language: "json",
    code: JSON.stringify(
      {
        agent_id: "expert",
        response_mode: "direct_expert",
        features: ["rag", "memory", "tools"]
      },
      null,
      2
    ),
    mustContain: ["agent_id", "direct_expert"]
  },
  {
    language: "html",
    code: [
      "<!doctype html>",
      '<html lang="en">',
      "  <body>",
      '    <main id="app">',
      '      <button type="button">Run & Verify</button>',
      "    </main>",
      "  </body>",
      "</html>"
    ].join("\n"),
    mustContain: ['<button type="button">Run & Verify</button>', "& Verify"]
  },
  {
    language: "sql",
    code: [
      "SELECT",
      "    user_id,",
      "    COUNT(*) AS request_count",
      "FROM request_logs",
      "WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'",
      "GROUP BY user_id;"
    ].join("\n"),
    mustContain: ["COUNT(*) AS request_count", "request_logs"]
  },
  {
    language: "markdown",
    code: [
      "# Build Notes",
      "",
      "Use `npm.cmd run build`.",
      "",
      "- Keep `_underscores_`",
      "- Keep `*asterisks*`",
      "- Keep `<tags>` when intentionally written"
    ].join("\n"),
    mustContain: ["# Build Notes", "_underscores_", "*asterisks*", "<tags>"]
  }
] satisfies { language: string; code: string; mustContain: string[] }[];

describe("SecureMarkdown", () => {
  it("does not render executable script elements from raw html", () => {
    const { container } = renderApp(
      <SecureMarkdown content={'<script>alert("x")</script><img src=x onerror=alert(1) />'} />
    );
    expect(container.querySelector("script")).not.toBeInTheDocument();
    expect(container.querySelector("img")).not.toBeInTheDocument();
  });

  it(
    "renders fenced code blocks with copy action",
    async () => {
      renderApp(<SecureMarkdown content={"```ts\nconst value = 1;\n```"} />);
      expect(screen.getByText("ts")).toBeInTheDocument();
      await userEvent.click(await screen.findByLabelText("Copy code"));
      expect(window.localStorage.getItem("test-clipboard")).toBe("const value = 1;");
    },
    30000
  );

  it.each(FIXTURES)(
    "preserves and copies literal $language fenced code without Markdown escaping",
    async ({ language, code, mustContain }) => {
      const markdown = fencedMarkdown(language, code);

      expect(extractFencedCode(markdown)).toEqual([{ language, code }]);

      renderApp(<SecureMarkdown content={markdown} />);
      await userEvent.click(await screen.findByLabelText("Copy code"));

      const copied = window.localStorage.getItem("test-clipboard");
      expect(copied).toBe(code);
      for (const expected of mustContain) {
        expect(copied).toContain(expected);
      }
      expect(copied).not.toContain("\\#");
      expect(copied).not.toContain("\\<");
      expect(copied).not.toContain("\\>");
      expect(copied).not.toContain("\\*");
      expect(copied).not.toContain("\\_");
    }
  );

  it("preserves inline code identifiers without underscore escaping", () => {
    renderApp(<SecureMarkdown content={"Use `response_model` and `get_db_session`."} />);

    expect(screen.getByText("response_model")).toBeInTheDocument();
    expect(screen.getByText("get_db_session")).toBeInTheDocument();
    expect(screen.queryByText("response\\_model")).not.toBeInTheDocument();
    expect(screen.queryByText("get\\_db\\_session")).not.toBeInTheDocument();
  });

  it("keeps Markdown features outside code while preserving fenced Markdown source", async () => {
    const markdownCode = [
      "# Heading",
      "",
      "**bold**",
      "",
      "`inline_code`",
      "",
      "snake_case",
      "",
      "<literal-example>"
    ].join("\n");
    renderApp(
      <SecureMarkdown
        content={[
          "# Rendered Heading",
          "",
          "**strong text**",
          "",
          "| key | value |",
          "| --- | --- |",
          "| link | [docs](https://example.com) |",
          "",
          "> quoted",
          "",
          fencedMarkdown("markdown", markdownCode)
        ].join("\n")}
      />
    );

    expect(screen.getByRole("heading", { name: "Rendered Heading" })).toBeInTheDocument();
    expect(screen.getByText("strong text")).toBeInTheDocument();
    expect(screen.getByText("quoted")).toBeInTheDocument();

    await userEvent.click(await screen.findByLabelText("Copy code"));
    expect(window.localStorage.getItem("test-clipboard")).toBe(markdownCode);
  });

  it("preserves UTF-8 and legitimate backslashes in copied source", async () => {
    const code = [
      'message = "café — 東京 — ✅"',
      'path = r"C:\\Projects\\HackerGPT Local"',
      'pattern = r"\\d+\\.\\d+"',
      "print(message)"
    ].join("\n");

    renderApp(<SecureMarkdown content={fencedMarkdown("python", code)} />);
    await userEvent.click(await screen.findByLabelText("Copy code"));

    expect(window.localStorage.getItem("test-clipboard")).toBe(code);
  });

  it("shows unsafe HTML as inert source inside code blocks", async () => {
    const code = '<script>alert("xss")</script>\n<img src=x onerror=alert(1)>';
    const { container } = renderApp(<SecureMarkdown content={fencedMarkdown("html", code)} />);

    expect(container.querySelector("script")).not.toBeInTheDocument();
    expect(container.querySelector("img")).not.toBeInTheDocument();

    await userEvent.click(await screen.findByLabelText("Copy code"));
    expect(window.localStorage.getItem("test-clipboard")).toBe(code);
  });

  it("handles empty and unknown-language code fences without mutation", async () => {
    const unknownCode = "alpha_beta * <tag>";
    renderApp(
      <SecureMarkdown
        content={[fencedMarkdown("unknownlang", unknownCode), "```text\n\n```"].join("\n\n")}
      />
    );

    const copyButtons = await screen.findAllByLabelText("Copy code");
    await userEvent.click(copyButtons[0]);
    expect(window.localStorage.getItem("test-clipboard")).toBe(unknownCode);

    await userEvent.click(copyButtons[1]);
    expect(window.localStorage.getItem("test-clipboard")).toBe("");
  });
});
