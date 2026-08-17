import { Check, Copy } from "lucide-react";
import { Children, lazy, Suspense, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

import { IconButton } from "../ui/IconButton";
import { useThemeStore } from "../../stores/themeStore";
import { getLanguageDisplayName } from "../../utils/languages";

const CodeBlockHighlighter = lazy(() => import("./CodeBlockHighlighter"));

type CodeProps = React.HTMLAttributes<HTMLElement> & {
  inline?: boolean;
  children?: React.ReactNode;
};

const LARGE_BLOCK_BYTES_THRESHOLD = 50000;
const LARGE_BLOCK_LINES_THRESHOLD = 2000;

export function SecureMarkdown({ content }: { content: string }) {
  const resolvedTheme = useThemeStore((state) => state.resolvedTheme);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSanitize]}
      components={{
        pre: ({ children }) => <>{children}</>,
        code: ({ inline, className, children, ...props }: CodeProps) => {
          const match = /language-([^\s]+)/.exec(className ?? "");
          const code = normalizeCodeNodeText(nodeToText(children));
          if (inline || !match) {
            return (
              <code
                className="rounded-md border border-border-subtle bg-elevated px-1 py-0.5 text-[0.9em] text-accent"
                {...props}
              >
                {children}
              </code>
            );
          }

          const rawLangTag = match[1];
          const filename = extractFilenameFromCode(code);
          const isTooLarge =
            code.length > LARGE_BLOCK_BYTES_THRESHOLD ||
            code.split("\n").length > LARGE_BLOCK_LINES_THRESHOLD;

          if (isTooLarge) {
            return <CodeBlockFallback code={code} language={rawLangTag} filename={filename} />;
          }

          return (
            <Suspense fallback={<CodeBlockFallback code={code} language={rawLangTag} filename={filename} />}>
              <CodeBlockHighlighter
                code={code}
                language={rawLangTag}
                filename={filename}
                dark={resolvedTheme === "dark"}
              />
            </Suspense>
          );
        }
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

function nodeToText(node: React.ReactNode): string {
  return Children.toArray(node)
    .map((child) => (typeof child === "string" || typeof child === "number" ? String(child) : ""))
    .join("");
}

function normalizeCodeNodeText(code: string): string {
  return code.endsWith("\n") ? code.slice(0, -1) : code;
}

function extractFilenameFromCode(code: string): string | undefined {
  const firstLine = (code.split("\n", 1)[0] ?? "").trim();
  const match = /^(?:\/\/|#|\/\*|<!--|;)\s*(?:file|filename|filepath):\s*([^\s*]+)/i.exec(firstLine);
  return match?.[1];
}

function CodeBlockFallback({
  code,
  language,
  filename
}: {
  code: string;
  language: string;
  filename?: string;
}) {
  const [copied, setCopied] = useState(false);
  const displayName = getLanguageDisplayName(language);

  return (
    <div className="my-3 overflow-hidden rounded-xl border border-border-subtle bg-surface/80 shadow-sm">
      <div className="flex items-center justify-between border-b border-border-subtle bg-elevated/70 px-3 py-1.5 text-xs text-muted">
        <div className="flex items-center gap-2 text-technical">
          <span>{language}</span>
          {displayName !== language && (
            <span className="text-[0.85em] opacity-75">({displayName})</span>
          )}
          {filename && (
            <span className="rounded bg-surface px-1.5 py-0.5 text-[0.85em] font-mono text-text">
              {filename}
            </span>
          )}
        </div>
        <IconButton
          label="Copy code"
          icon={copied ? <Check size={15} /> : <Copy size={15} />}
          className="size-7"
          onClick={() => {
            void navigator.clipboard.writeText(code);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1200);
          }}
        />
      </div>
      <pre className="overflow-auto p-4 text-sm font-mono leading-relaxed text-text">
        {code}
      </pre>
    </div>
  );
}
