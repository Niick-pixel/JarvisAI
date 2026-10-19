// Agent mode, in the conversation: what a tool sent back (folded, it is data, not your words) and
// every call waiting for you, asked right where the answer is being written.
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, ShieldCheck, Wrench } from "lucide-react";
import { useState } from "react";
import type { Message } from "../api/types";
import { useChatAgent } from "../store/chatAgent";
import { Button } from "../ui/controls";
import { BOUNCE } from "../ui/motion";
import { type Outcome as Item, outcomes } from "./toolResults";

function Outcome({ item }: { item: Item }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-2xl border border-ink/[0.07] bg-ink/[0.02]">
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px]">
        <ChevronRight size={14} className={`shrink-0 text-ink-faint transition-transform ${open ? "rotate-90" : ""}`} />
        <Wrench size={14} strokeWidth={1.75} className="shrink-0 text-ink-muted" />
        <span className="font-medium text-ink">{item.tool}</span>
        <span className="min-w-0 flex-1 truncate font-mono text-[12px] text-ink-muted">{item.target}</span>
        <span className={`text-[12px] ${item.ran ? "text-success" : "text-ink-faint"}`}>{item.ran ? "ran" : "skipped"}</span>
      </button>
      {open && (
        <pre className="scroll-quiet mx-3 mb-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-xl bg-code p-3 font-mono text-[11.5px] text-ink">
          {item.output || "(no output)"}
        </pre>
      )}
    </div>
  );
}

export function ToolResults({ message }: { message: Message }) {
  const items = outcomes(message.content);
  return (
    <div className="flex flex-col gap-1.5 pl-[42px]">
      {items.map((item, i) => (
        <Outcome key={i} item={item} />
      ))}
    </div>
  );
}

export function PendingCalls() {
  const calls = useChatAgent((s) => s.calls).filter((c) => c.status === "pending");
  const busy = useChatAgent((s) => s.busy);
  const decide = useChatAgent((s) => s.decide);
  return (
    <AnimatePresence>
      {calls.map((call) => (
        <motion.div
          key={call.id}
          layout
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.97 }}
          transition={BOUNCE}
          className="ml-[42px] rounded-3xl border border-accent/25 bg-raised p-4 shadow-card"
        >
          <div className="flex items-start gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/12 text-accent">
              <ShieldCheck size={16} strokeWidth={1.75} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-medium text-ink">Jarvis wants to use {call.tool}</p>
              <p className="mt-1 break-all rounded-xl bg-code px-2.5 py-1.5 font-mono text-[12px] text-ink">{call.target}</p>
              {call.args_preview && <p className="mt-1 line-clamp-3 break-all font-mono text-[11.5px] text-ink-faint">{call.args_preview}</p>}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap justify-end gap-1.5">
            <Button small tone="ghost" disabled={busy === call.id} onClick={() => void decide(call.id, false, false)}>
              Deny
            </Button>
            <Button small disabled={busy === call.id} onClick={() => void decide(call.id, true, true)} title="Approve, and stop asking for this tool here">
              Always allow here
            </Button>
            <Button small tone="primary" disabled={busy === call.id} onClick={() => void decide(call.id, true, false)}>
              Allow once
            </Button>
          </div>
        </motion.div>
      ))}
    </AnimatePresence>
  );
}
