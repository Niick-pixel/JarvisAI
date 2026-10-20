// While a model loads, the chat cannot answer - so the window says so, plainly: which model, the
// stage llama-server has reached, how long it has taken, and a bar towards how long it took last
// time. It disappears the moment the model is ready.
import { AnimatePresence, motion } from "framer-motion";
import { useHud } from "../store/hud";

export default function LoadingBar() {
  const job = useHud((s) => s.sample?.activity.find((a) => a.kind === "model"));
  const pct = job?.progress == null ? null : Math.round(job.progress * 100);
  return (
    <AnimatePresence>
      {job && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="relative z-10 mx-auto mb-1 w-full max-w-[760px] px-4"
          role="status"
        >
          <div className="flex items-baseline gap-2 text-[12.5px]">
            <span className="min-w-0 flex-1 truncate font-medium text-ink">{job.label.replace(/\.gguf$/i, "")}</span>
            <span className="shrink-0 tabular-nums text-ink-faint">
              {job.detail || "Starting"} · {job.seconds ?? 0}s{pct != null ? ` · ~${pct}%` : ""}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
            {pct != null ? (
              <div className="h-full rounded-full bg-[#E5322D] transition-[width] duration-700" style={{ width: `${pct}%` }} />
            ) : (
              <div className="h-full w-1/3 animate-[slide_1.4s_ease-in-out_infinite] rounded-full bg-[#E5322D]/70" />
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
