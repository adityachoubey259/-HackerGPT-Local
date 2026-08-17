import { Check, Copy } from "lucide-react";
import { Children, lazy, Suspense, useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

import { IconButton } from "../ui/IconButton";
import { useThemeStore } from "../../stores/themeStore";

const CodeBlockHighlighter = lazy(() => import("./CodeBlockHighlighter"));

type CodeProps = React.HTMLAttributes<HTMLElement> & {
  inline?: boolean;
  children?: React.ReactNode;
};

export function SecureMarkdown({ content }: { content: string }) {
  const resolvedTheme = useThemeStore((state) => state.resolvedTheme);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSanitize]}
      components={{
        pre: ({ children }) => <>{children}</>,
        code: ({ inline, className, children, ...props }: CodeProps) => {
          const match = /language-(\w+)/.exec(className ?? "");
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
          return (
            <Suspense fallback={<CodeBlockFallback code={code} language={match[1]} />}>
              <CodeBlockHighlighter
                code={code}
                language={match[1]}
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

function CodeBlockFallback({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="my-3 overflow-hidden rounded-xl border border-border-subtle bg-surface/80 shadow-sm">
      <div className="flex items-center justify-between border-b border-border-subtle bg-elevated/70 px-3 py-1.5 text-xs text-muted">
        <span className="text-technical">{language}</span>
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
      <pre className="overflow-auto p-4 text-sm">
        {code}
      </pre>
    </div>
  );
}
