// The morning briefing, waiting on Home: today's one, readable in place, ready to read aloud or to
// ask about. Asked for on demand too, from the "Brief me" button underneath the composer.
import { motion } from "framer-motion";
import { MessageSquare, RefreshCw, Square, Sun, Volume2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useBriefing } from "../store/briefing";
import { useSession } from "../store/session";
import { useVoice } from "../store/voice";
import { IconButton } from "../ui/controls";
import { BOUNCE } from "../ui/motion";
import Markdown from "./Markdown";

const FRESH_MS = 18 * 3_600_000;

export default function BriefingCard() {
  const { latest, settings, running, load, run, markRead } = useBriefing();
  const speak = useVoice((s) => s.speak);
  const hush = useVoice((s) => s.hush);
  const speaking = useVoice((s) => latest !== null && s.speakingId === latest.id);
  const [hidden, setHidden] = useState(false);

  useEffect(() => void load().catch(() => undefined), [load]);
  const fresh = latest && Date.now() - latest.created_at < FRESH_MS;

  useEffect(() => {
    // Read aloud once, the first time Home is opened after it was written - never on every visit.
    if (fresh && latest && !latest.read_at && settings?.speak) {
      void speak(latest.id, latest.body);
      void markRead();
    }
  }, [fresh, latest, settings?.speak, speak, markRead]);

  if (!fresh || !latest || hidden) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={BOUNCE}
      className="mb-5 rounded-3xl border border-ink/[0.07] bg-surface/80 p-5 shadow-card backdrop-blur"
    >
      <div className="mb-2 flex items-center gap-2">
        <Sun size={17} strokeWidth={1.75} className="text-accent" />
        <p className="flex-1 text-[13px] font-semibold text-ink-muted">{latest.title}</p>
        <IconButton icon={speaking ? Square : Volume2} label={speaking ? "Stop reading" : "Read aloud"} size={30} active={speaking} onClick={() => (speaking ? hush() : void speak(latest.id, latest.body))} />
        <IconButton icon={RefreshCw} label={running ? "Writing…" : "Write a fresh one"} size={30} disabled={running} onClick={() => void run()} />
        {latest.conversation_id && (
          <IconButton icon={MessageSquare} label="Ask about it" size={30} onClick={() => void useSession.getState().openConversation(latest.conversation_id ?? "")} />
        )}
        <IconButton
          icon={X}
          label="Hide"
          size={30}
          onClick={() => {
            setHidden(true);
            void markRead();
          }}
        />
      </div>
      <div className={`text-[14.5px] ${running ? "opacity-50" : ""}`}>
        <Markdown text={latest.body} />
      </div>
    </motion.div>
  );
}
