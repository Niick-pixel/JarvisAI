// Short notes at the bottom of the screen. Voice problems land here too, as sentences.
import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { toast, useToasts } from "../store/toast";
import { useVoice } from "../store/voice";
import { BOUNCE } from "../ui/motion";

export default function Toasts() {
  const toasts = useToasts((s) => s.toasts);
  const voiceError = useVoice((s) => s.error);

  useEffect(() => {
    if (!voiceError) return;
    toast(voiceError, "error");
    useVoice.getState().dismiss();
  }, [voiceError]);

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-[60] flex flex-col items-center gap-2 px-6">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, y: 16, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={BOUNCE}
            className={`max-w-lg rounded-full px-5 py-2.5 text-center text-[13.5px] shadow-float ${
              t.tone === "error" ? "bg-danger text-bg" : "bg-ink text-bg"
            }`}
          >
            {t.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
