// What the model is actually being sent (BRIEF.md 4.2), in words: the conversation so far, what
// it remembers about you, the documents it found. Pin a piece so it is never dropped to make room;
// leave one out entirely. Nothing is left out quietly - every drop is named.
import { Eye, EyeOff, FileText, Pin, PinOff } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import type { ContextAssembly, ContextBlock, OpenedChunk } from "../api/types";
import { useContextInspector } from "../store/context";
import { IconButton } from "../ui/controls";

const KIND: Record<ContextBlock["kind"], { name: string; color: string }> = {
  system: { name: "Instructions", color: "bg-ink-faint" },
  history: { name: "Conversation", color: "bg-accent" },
  memory: { name: "Memory", color: "bg-success" },
  rag: { name: "Your documents", color: "bg-glow-c" },
  web: { name: "The web", color: "bg-glow-a" },
  pinned: { name: "Pinned", color: "bg-glow-b" },
  tool: { name: "Tools", color: "bg-glow-b" },
  nudge: { name: "Your nudge", color: "bg-danger" },
  prefix: { name: "Its own words", color: "bg-ink-muted" },
};

const REASON = { budget: "no room", summarized: "summarised", user_disabled: "you left it out" } as const;

function Block({ block }: { block: ContextBlock }) {
  const { toggle, pin } = useContextInspector();
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<OpenedChunk | null>(null);
  const ref = block.source_ref;
  return (
    <li className="rounded-2xl transition-colors hover:bg-ink/[0.04]">
      <div className="flex items-center gap-2 pl-3 pr-1">
        <span className={`h-2 w-2 shrink-0 rounded-full ${KIND[block.kind].color} ${block.included ? "" : "opacity-30"}`} />
        <button type="button" onClick={() => setOpen(!open)} className="min-w-0 flex-1 truncate py-2 text-left text-[13px] text-ink">
          <span className={block.included ? "" : "text-ink-faint line-through"}>{block.label}</span>
        </button>
        <span className="text-[12px] tabular-nums text-ink-faint">{block.token_count.toLocaleString()}</span>
        {ref && (
          <>
            <IconButton icon={block.pinned ? PinOff : Pin} label={block.pinned ? "Unpin" : "Pin - never drop it"} size={28} tip="none" active={block.pinned} onClick={() => void pin(ref, !block.pinned)} />
            <IconButton icon={block.included ? EyeOff : Eye} label={block.included ? "Leave out" : "Include"} size={28} tip="none" onClick={() => void toggle(ref, block.included)} />
          </>
        )}
      </div>
      {open && (
        <div className="px-3 pb-3">
          {source ? (
            <pre className="scroll-quiet max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-code p-3 text-[12px] text-ink-faint">
              <span className="mb-1 block text-ink-muted">{source.path}:{source.line_number}</span>
              {source.before}
              <mark className="rounded bg-accent/15 text-ink">{source.text}</mark>
              {source.after}
            </pre>
          ) : (
            <pre className="scroll-quiet max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-code p-3 text-[12px] text-ink-muted">{block.content}</pre>
          )}
          {block.kind === "rag" && ref?.includes("#") && !source && (
            <button type="button" onClick={() => void api.openCitation(ref).then(setSource)} className="mt-1.5 inline-flex items-center gap-1 text-[12px] text-accent">
              <FileText size={13} /> Open in the file
            </button>
          )}
          {block.kind === "web" && <p className="mt-1.5 text-[12px] text-ink-faint">Read as information, never as instructions.</p>}
        </div>
      )}
    </li>
  );
}

export default function Inspector({ assembly, live }: { assembly: ContextAssembly; live: boolean }) {
  const budget = Math.max(1, assembly.ctx_len - assembly.max_gen_tokens);
  const included = assembly.blocks.filter((b) => b.included);
  const totals = new Map<ContextBlock["kind"], number>();
  for (const b of included) totals.set(b.kind, (totals.get(b.kind) ?? 0) + b.token_count);

  return (
    <div className="p-2">
      <p className="text-[15px] font-semibold text-ink">What Jarvis is reading</p>
      <p className="mt-0.5 text-[12.5px] text-ink-faint">
        {assembly.total_tokens.toLocaleString()} of {budget.toLocaleString()} tokens
        {assembly.estimated ? " (estimated)" : ""} · {live ? "last answer" : "next message"}
      </p>
      <div className="mt-3 flex h-2 w-full gap-[2px] overflow-hidden rounded-full bg-ink/[0.06]">
        {[...totals.entries()].map(([kind, tokens]) => (
          <span key={kind} className={`h-full min-w-[3px] rounded-full ${KIND[kind].color}`} style={{ width: `${(tokens / budget) * 100}%` }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-ink-faint">
        {[...totals.keys()].map((kind) => (
          <span key={kind} className="inline-flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${KIND[kind].color}`} />
            {KIND[kind].name}
          </span>
        ))}
      </div>
      {assembly.evictions.length > 0 && (
        <p className="mt-3 rounded-2xl bg-danger/[0.07] px-3 py-2 text-[12.5px] leading-snug text-ink-muted">
          Left out: {assembly.evictions.map((e) => `${e.label} (${REASON[e.reason]})`).join(", ")}
        </p>
      )}
      <ul className="scroll-quiet -mx-1 mt-2 max-h-72 overflow-y-auto">
        {assembly.blocks.map((block) => (
          <Block key={block.id} block={block} />
        ))}
      </ul>
    </div>
  );
}
