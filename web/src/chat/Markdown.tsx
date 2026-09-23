// Answers are Markdown; they are rendered, never shown as asterisks. Links open outside the app,
// and code gets a header with its language and a copy button, like every assistant worth using.
import { Check, Copy } from "lucide-react";
import { memo, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="overflow-hidden rounded-2xl border border-ink/[0.06] bg-code">
      <div className="flex h-9 items-center justify-between pl-4 pr-1.5 text-[12px] text-ink-faint">
        <span>{language || "text"}</span>
        <button
          type="button"
          onClick={() => {
            void navigator.clipboard?.writeText(code).then(() => {
              setCopied(true);
              window.setTimeout(() => setCopied(false), 1400);
            });
          }}
          className="inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 transition-colors hover:bg-ink/[0.06] hover:text-ink"
        >
          {copied ? <Check size={14} strokeWidth={2} /> : <Copy size={14} strokeWidth={1.75} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="scroll-quiet overflow-x-auto px-4 pb-4 font-mono text-[13px] leading-relaxed text-ink">
        <code>{code}</code>
      </pre>
    </div>
  );
}

const components: Components = {
  pre: ({ children }) => <>{children}</>,
  code: ({ className, children }) => {
    const match = /language-(\w+)/.exec(className ?? "");
    const text = String(children ?? "");
    // Fenced blocks carry a language class or span lines; everything else is inline code.
    if (match || text.includes("\n")) return <CodeBlock language={match?.[1] ?? ""} code={text.replace(/\n$/, "")} />;
    return <code>{children}</code>;
  },
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer noopener">
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="scroll-quiet overflow-x-auto rounded-2xl border border-ink/[0.08]">
      <table>{children}</table>
    </div>
  ),
};

function Markdown({ text }: { text: string }) {
  return (
    <div className="prose-jarvis">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}

export default memo(Markdown);
