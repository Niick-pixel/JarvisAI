// The one place an update asks for anything: a row above Settings once the new version is
// downloaded and verified. Until then updating is invisible, the way a good app's is.
import { AnimatePresence, motion } from "framer-motion";
import { ArrowDownToLine, RotateCw } from "lucide-react";
import { useEffect } from "react";
import { useUpdates, watchUpdates } from "../store/updates";
import { BOUNCE } from "../ui/motion";

export default function UpdateRow({ open }: { open: boolean }) {
  const status = useUpdates((s) => s.status);
  const install = useUpdates((s) => s.install);
  const download = useUpdates((s) => s.download);
  useEffect(() => watchUpdates(), []);

  const ready = status?.state === "ready" || status?.state === "installing";
  // Automatic updates off: say a version exists, and let one click fetch it.
  const offered =
    status?.state === "available" && status.can_install && !status.auto;
  if (!ready && !offered) return null;

  const label =
    status?.state === "installing"
      ? "Restarting…"
      : ready
        ? "Restart to update"
        : `Get Jarvis ${status?.latest}`;
  const Icon = ready ? RotateCw : ArrowDownToLine;
  return (
    <AnimatePresence>
      <motion.button
        type="button"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={BOUNCE}
        disabled={status?.state === "installing"}
        title={open ? undefined : `${label} - Jarvis ${status?.latest}`}
        onClick={() => void (ready ? install() : download())}
        className={`flex h-10 w-full items-center gap-3 rounded-full bg-accent/12 text-[14px] font-medium text-accent transition-colors hover:bg-accent/20 ${open ? "px-3" : "justify-center"}`}
      >
        <Icon size={19} strokeWidth={1.9} className="shrink-0" />
        {open && <span className="truncate">{label}</span>}
      </motion.button>
    </AnimatePresence>
  );
}
