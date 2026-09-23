// A new chat: the mark, a greeting, and the composer in the middle of the room. A few real
// starting points underneath - each one does something, none of them is a canned prompt.
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { AudioLines, BookOpen, Globe, Users } from "lucide-react";
import Orb from "../brand/Orb";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";
import { BOUNCE } from "../ui/motion";
import Composer from "./Composer";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Up late";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function Start({ icon: Icon, label, onClick, i }: { icon: LucideIcon; label: string; onClick: () => void; i: number }) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...BOUNCE, delay: 0.18 + i * 0.05 }}
      whileTap={{ scale: 0.95 }}
      className="inline-flex h-10 items-center gap-2 rounded-full border border-ink/[0.08] bg-surface/70 px-4 text-[14px] text-ink-muted backdrop-blur transition-colors hover:bg-surface hover:text-ink"
    >
      <Icon size={17} strokeWidth={1.75} />
      {label}
    </motion.button>
  );
}

export default function Home() {
  const name = useUi((s) => s.name);
  const openSheet = useUi((s) => s.openSheet);
  const setVoiceMode = useUi((s) => s.setVoiceMode);
  const setResearch = useSession((s) => s.setResearch);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col items-center justify-center px-6 pb-16">
      <div className="w-full max-w-[760px]">
        <motion.div
          initial={{ opacity: 0, y: 14, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={BOUNCE}
          className="mb-8 px-2"
        >
          <Orb size={44} />
          <h1 className="mt-5 font-display text-[40px] font-semibold leading-tight tracking-tight">
            <span className="gradient-text">
              {greeting()}
              {name ? `, ${name}` : ""}
            </span>
          </h1>
          <p className="font-display text-[40px] font-semibold leading-tight tracking-tight text-ink-faint">
            How can I help?
          </p>
        </motion.div>
        <motion.div layoutId="composer" transition={BOUNCE}>
          <Composer autoFocus />
        </motion.div>
        <div className="mt-5 flex flex-wrap gap-2 px-1">
          <Start i={0} icon={AudioLines} label="Talk" onClick={() => setVoiceMode(true)} />
          <Start i={1} icon={Globe} label="Research" onClick={() => setResearch(true)} />
          <Start i={2} icon={Users} label="Ask the council" onClick={() => openSheet("council")} />
          <Start i={3} icon={BookOpen} label="Add your documents" onClick={() => openSheet("knowledge")} />
        </div>
      </div>
    </div>
  );
}
