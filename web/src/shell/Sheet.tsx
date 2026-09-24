// One sheet at a time, centred over a softened app. Memory, Knowledge, Agents, Settings and the
// Council all live in one of these; opening another replaces it rather than stacking beside it.
import { motion } from "framer-motion";
import { X } from "lucide-react";
import { type ReactNode, useEffect } from "react";
import { useUi } from "../store/ui";
import { IconButton } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

export default function Sheet({
  title,
  subtitle,
  actions,
  children,
  width = 720,
  onClose,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  width?: number;
  /** For dialogs that are not one of the sidebar's sheets, like model downloads. */
  onClose?: () => void;
}) {
  const closeSheet = useUi((s) => s.closeSheet);
  const close = onClose ?? closeSheet;

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-6">
      <motion.div
        className="absolute inset-0 bg-bg/55 backdrop-blur-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={close}
      />
      <motion.section
        role="dialog"
        aria-label={title}
        initial={{ opacity: 0, scale: 0.94, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.97, y: 8, transition: { duration: 0.15 } }}
        transition={BOUNCE}
        style={{ maxWidth: width }}
        className="relative flex max-h-[min(86vh,860px)] w-full flex-col overflow-hidden rounded-4xl border border-ink/[0.06] bg-surface shadow-float"
      >
        <header className="flex items-start gap-3 px-7 pb-3 pt-6">
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-[22px] font-semibold tracking-tight text-ink">{title}</h2>
            {subtitle && <p className="mt-0.5 text-[13px] text-ink-faint">{subtitle}</p>}
          </div>
          {actions}
          <IconButton icon={X} label="Close" onClick={close} tip="none" />
        </header>
        <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto px-7 pb-7">{children}</div>
      </motion.section>
    </div>
  );
}
