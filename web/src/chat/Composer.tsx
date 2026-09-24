// The composer: one soft pill. Tools on the left, mic and send on the right. While Jarvis is
// answering, what you type steers the answer instead of queueing behind it - Enter sends a nudge,
// the run keeps what it wrote and carries on with your note in mind.
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, AudioLines, Mic, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useSession } from "../store/session";
import { toast } from "../store/toast";
import { useUi } from "../store/ui";
import { useVoice } from "../store/voice";
import { IconButton } from "../ui/controls";
import { BOUNCE } from "../ui/motion";
import ComposerTools from "./ComposerTools";
import ContextRing from "./ContextRing";

type Kind = "send" | "stop" | "voice";
const PRIMARY: Record<Kind, { icon: typeof ArrowUp; label: string }> = {
  send: { icon: ArrowUp, label: "Send" },
  stop: { icon: Square, label: "Stop" },
  voice: { icon: AudioLines, label: "Talk to Jarvis" },
};

function Primary({ kind, onClick }: { kind: Kind; onClick: () => void }) {
  const { icon: Icon, label } = PRIMARY[kind];
  return (
    <motion.button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      whileTap={{ scale: 0.88 }}
      transition={BOUNCE}
      className="relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-ink text-bg"
    >
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={kind}
          initial={{ scale: 0.4, opacity: 0, rotate: -30 }}
          animate={{ scale: 1, opacity: 1, rotate: 0 }}
          exit={{ scale: 0.4, opacity: 0 }}
          transition={BOUNCE}
          className="flex"
        >
          {kind === "stop" ? (
            <Icon size={14} strokeWidth={0} fill="currentColor" />
          ) : (
            <Icon size={20} strokeWidth={2} />
          )}
        </motion.span>
      </AnimatePresence>
    </motion.button>
  );
}

export default function Composer({ autoFocus }: { autoFocus?: boolean }) {
  const [draft, setDraft] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);
  const send = useSession((s) => s.send);
  const stop = useSession((s) => s.stop);
  const runId = useSession((s) => s.runId);
  const phase = useVoice((s) => s.phase);
  const dictated = useVoice((s) => s.dictated);
  const stt = useVoice((s) => s.status?.stt);
  const setVoiceMode = useUi((s) => s.setVoiceMode);
  const running = runId !== null;
  const empty = draft.trim() === "";

  useEffect(() => {
    // Dictation lands in the box, not the conversation: you read it before it is sent.
    // In voice mode the conversation loop takes it instead.
    if (!dictated || useUi.getState().voiceMode) return;
    setDraft((current) => (current ? `${current.trimEnd()} ${dictated}` : dictated));
    useVoice.getState().consume();
    area.current?.focus();
  }, [dictated]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || useUi.getState().sheet) return;
      if (phase === "listening") useVoice.getState().cancel();
      else if (runId) void stop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [runId, stop, phase]);

  useEffect(() => {
    // Grow with the text, up to a point, then scroll.
    const el = area.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [draft]);

  const nudge = async (note: string) => {
    const { runId: id, conversation, runStream } = useSession.getState();
    if (!id || !conversation) return;
    // Records where it landed and stops the run, leaving the partial settled on disk.
    const { message_id } = await api.nudge(id, note);
    await runStream({ conversation_id: conversation.id, continue_from: message_id, nudge: note });
  };

  const submit = () => {
    const content = draft.trim();
    if (!content) return;
    setDraft("");
    if (running) void nudge(content).catch(() => toast("Couldn't steer that answer", "error"));
    else void send(content);
  };

  const mic = () => {
    const voice = useVoice.getState();
    if (!stt?.available) {
      toast(stt ? `${stt.reason} ${stt.fix ?? ""}`.trim() : "Voice is still starting up", "error");
      return;
    }
    if (phase === "listening") void voice.finish();
    else if (phase === "idle") void voice.listen();
  };

  const placeholder =
    phase === "listening"
      ? "Listening…"
      : phase === "transcribing"
        ? "Writing down what you said…"
        : running
          ? "Steer the answer - Enter to nudge, Esc to stop"
          : "Ask Jarvis";

  return (
    <div className="relative rounded-[28px] border border-ink/[0.07] bg-surface p-2 shadow-float transition-colors focus-within:border-ink/[0.14]">
      <textarea
        ref={area}
        value={draft}
        autoFocus={autoFocus}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        rows={1}
        placeholder={placeholder}
        className="block max-h-[220px] min-h-[44px] w-full resize-none bg-transparent px-4 pb-1 pt-3 text-[16px] leading-relaxed text-ink outline-none placeholder:text-ink-faint"
      />
      <div className="flex items-center gap-1 pt-1">
        <ComposerTools />
        <div className="ml-auto flex items-center gap-1">
          <ContextRing />
          <IconButton
            icon={Mic}
            label={phase === "listening" ? "Stop and write it down" : "Dictate"}
            active={phase === "listening"}
            disabled={phase === "transcribing"}
            onClick={mic}
            size={40}
            tip="top"
            className={phase === "listening" ? "animate-pulse" : ""}
          />
          {running && empty ? (
            <Primary kind="stop" onClick={() => void stop()} />
          ) : empty ? (
            <Primary kind="voice" onClick={() => setVoiceMode(true)} />
          ) : (
            <Primary kind="send" onClick={submit} />
          )}
        </div>
      </div>
    </div>
  );
}
