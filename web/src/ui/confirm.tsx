// A question that has to be answered before something expensive happens - a 13 GB download, a
// model that will make the PC stutter. One at a time, on top of everything, with the cautious
// choice focused so Enter never commits by accident.
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { create } from "zustand";
import { Button } from "./controls";
import { GLIDE } from "./motion";

interface Question {
  title: string;
  body: string;
  confirm: string;
  danger?: boolean;
}

interface ConfirmState {
  question: Question | null;
  resolve: ((yes: boolean) => void) | null;
  ask: (question: Question) => Promise<boolean>;
  answer: (yes: boolean) => void;
}

export const useConfirm = create<ConfirmState>((set, get) => ({
  question: null,
  resolve: null,
  ask: (question) =>
    new Promise<boolean>((resolve) => {
      get().resolve?.(false);
      set({ question, resolve });
    }),
  answer: (yes) => {
    get().resolve?.(yes);
    set({ question: null, resolve: null });
  },
}));

export function ConfirmHost() {
  const { question, answer } = useConfirm();
  return (
    <AnimatePresence>
      {question && (
        <motion.div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-ink/30 px-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => answer(false)}
        >
          <motion.div
            role="alertdialog"
            aria-labelledby="confirm-title"
            className="w-full max-w-md rounded-3xl bg-surface p-6 shadow-xl"
            initial={{ y: 12, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            transition={GLIDE}
            onClick={(e) => e.stopPropagation()}
          >
            <p
              id="confirm-title"
              className="flex items-center gap-2 text-[17px] font-medium text-ink"
            >
              <AlertTriangle
                size={20}
                strokeWidth={2}
                className={question.danger ? "text-danger" : "text-accent"}
              />
              {question.title}
            </p>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">
              {question.body}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button tone="primary" autoFocus onClick={() => answer(false)}>
                Cancel
              </Button>
              <Button
                tone={question.danger ? "danger" : "secondary"}
                onClick={() => answer(true)}
              >
                {question.confirm}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
