// The gate, as a notification. A job is parked waiting for this answer, so it appears in the
// corner wherever you are instead of hiding inside a panel while the run stalls.
//
// The target is shown verbatim and never truncated: it is the thing you are approving.
import { AnimatePresence, motion } from "framer-motion";
import { ShieldCheck } from "lucide-react";
import { useAgents } from "../store/agents";
import { Button } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

export default function Approvals() {
  const pending = useAgents((s) => s.pending);
  const busy = useAgents((s) => s.busy);
  const decide = useAgents((s) => s.decide);

  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[380px] max-w-[calc(100vw-40px)] flex-col gap-3">
      <AnimatePresence>
        {pending.map((call) => (
          <motion.div
            key={call.id}
            layout
            initial={{ opacity: 0, x: 40, scale: 0.96 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40, scale: 0.96 }}
            transition={BOUNCE}
            className="pointer-events-auto rounded-3xl border border-ink/[0.06] bg-raised p-4 shadow-float"
          >
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent/12 text-accent">
                <ShieldCheck size={18} strokeWidth={1.75} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-medium text-ink">
                  {call.job_name ? `"${call.job_name}"` : "An agent"} wants to use {call.tool}
                </p>
                <p className="mt-1 break-all rounded-xl bg-code px-2.5 py-1.5 font-mono text-[12px] text-ink">{call.target}</p>
                {call.args_preview && (
                  <p className="mt-1 line-clamp-3 break-all font-mono text-[11.5px] text-ink-faint">{call.args_preview}</p>
                )}
              </div>
            </div>
            <div className="mt-3 flex flex-wrap justify-end gap-1.5">
              <Button small tone="ghost" disabled={busy === call.id} onClick={() => void decide(call.id, false, false)}>
                Deny
              </Button>
              <Button
                small
                disabled={busy === call.id}
                onClick={() => void decide(call.id, true, true)}
                title="Approve, and stop asking for this tool in this folder or on this site"
              >
                Always allow here
              </Button>
              <Button small tone="primary" disabled={busy === call.id} onClick={() => void decide(call.id, true, false)}>
                Allow once
              </Button>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
