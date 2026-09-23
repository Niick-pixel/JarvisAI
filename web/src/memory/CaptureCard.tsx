// "Remembered 2 things", with what they were and one click to undo.
//
// This is the difference between capture that is automatic and capture that is silent: you see
// every fact the moment it is written, and taking it back is one click, not an archaeology dig.
import { AnimatePresence, motion } from "framer-motion";
import { Brain } from "lucide-react";
import { useEffect } from "react";
import { useMemory } from "../store/memory";
import { Button } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

export default function CaptureCard() {
  const batch = useMemory((s) => s.lastCapture);
  const undo = useMemory((s) => s.undoCapture);
  const dismiss = useMemory((s) => s.dismissCapture);
  const count = batch?.entries.length ?? 0;

  useEffect(() => {
    // It steps aside on its own; keeping what was learned is the default, not a chore.
    if (!batch) return;
    const timer = window.setTimeout(dismiss, 9000);
    return () => window.clearTimeout(timer);
  }, [batch, dismiss]);

  return (
    <AnimatePresence>
      {batch && count > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -12, scale: 0.97 }}
          transition={BOUNCE}
          className="fixed right-5 top-16 z-50 w-[340px] rounded-3xl border border-ink/[0.06] bg-raised p-4 shadow-float"
        >
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-success/12 text-success">
              <Brain size={18} strokeWidth={1.75} />
            </span>
            <p className="flex-1 text-[14px] font-medium text-ink">
              Remembered {count === 1 ? "one thing" : `${count} things`}
            </p>
            <Button small tone="ghost" onClick={() => void undo()} title="Forget exactly what this wrote">
              Undo
            </Button>
          </div>
          <ul className="mt-2 space-y-1 pl-12">
            {batch.entries.map((entry) => (
              <li key={entry.id} className="line-clamp-2 text-[13px] leading-snug text-ink-muted">
                {entry.content}
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
