// A reasoning model's thinking, folded away: "Thinking…" shimmering while it happens, "Thought for
// 6s" once it is done. Open it and the thoughts are there, quieter than the answer.
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { useState } from "react";
import { GLIDE } from "../ui/motion";

function seconds(ms: number): string {
  const s = Math.max(1, Math.round(ms / 1000));
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`;
}

export default function Thinking({ text, live, ms }: { text: string; live: boolean; ms?: number }) {
  const [open, setOpen] = useState(false);
  const label = live ? "Thinking" : ms ? `Thought for ${seconds(ms)}` : "Show thinking";

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex h-8 items-center gap-1 rounded-full pl-1 pr-3 text-[14px] text-ink-faint transition-colors hover:text-ink"
      >
        <ChevronRight size={16} strokeWidth={2} className={`transition-transform ${open ? "rotate-90" : ""}`} />
        <span className={live ? "shimmer font-medium" : ""}>{label}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={GLIDE}
            className="overflow-hidden"
          >
            <p className="ml-2.5 mt-1 whitespace-pre-wrap border-l-2 border-ink/10 py-1 pl-4 text-[14px] leading-relaxed text-ink-faint">
              {text || "…"}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
