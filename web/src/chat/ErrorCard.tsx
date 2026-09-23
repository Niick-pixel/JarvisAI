// When something goes wrong it says so in the conversation, in a sentence, with the one button
// that fixes it - the backend sends a machine-readable remedy with every error.
import { AnimatePresence, motion } from "framer-motion";
import { TriangleAlert } from "lucide-react";
import { useSession } from "../store/session";
import { Button } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

export default function ErrorCard() {
  const error = useSession((s) => s.error);
  const applyRemedy = useSession((s) => s.applyRemedy);
  const dismiss = useSession((s) => s.dismissError);

  return (
    <AnimatePresence>
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={BOUNCE}
          className="flex items-start gap-3 rounded-3xl border border-danger/15 bg-danger/[0.06] p-4 pl-5"
        >
          <TriangleAlert size={20} strokeWidth={1.75} className="mt-0.5 shrink-0 text-danger" />
          <div className="min-w-0 flex-1">
            <p className="text-[14.5px] leading-snug text-ink">{error.message}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {error.remedy && (
                <Button tone="primary" small onClick={() => void applyRemedy(error.remedy!)}>
                  {error.remedy.label}
                </Button>
              )}
              <Button tone="ghost" small onClick={dismiss}>
                Dismiss
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
