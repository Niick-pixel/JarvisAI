// The images going with the next message, above the text box. Click the x to leave one out.
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useAttachments } from "../store/attachments";
import { BOUNCE } from "../ui/motion";

export default function AttachmentTray() {
  const { pending, busy, remove } = useAttachments();
  if (pending.length === 0 && !busy) return null;
  return (
    <div className="flex flex-wrap gap-2 px-3 pt-2">
      <AnimatePresence initial={false}>
        {pending.map((a) => (
          <motion.div
            key={a.id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={BOUNCE}
            className="group relative h-16 w-16 overflow-hidden rounded-2xl border border-ink/[0.08] bg-ink/[0.03]"
          >
            <img src={a.url} alt={a.source === "screen" ? "Screenshot" : "Image"} className="h-full w-full object-cover" />
            <button
              type="button"
              aria-label="Remove image"
              onClick={() => remove(a.id)}
              className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-ink/70 text-bg opacity-0 transition-opacity group-hover:opacity-100"
            >
              <X size={12} strokeWidth={2.5} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
      {busy && <div className="shimmer flex h-16 w-16 items-center justify-center rounded-2xl bg-ink/[0.04] text-[11px]">Adding…</div>}
    </div>
  );
}
