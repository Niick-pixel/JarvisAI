// Voice mode: the whole window becomes the orb. It listens, answers out loud, and listens again -
// the same experience a speaker in the kitchen would have, which is where this is heading.
import { AnimatePresence, motion } from "framer-motion";
import { Mic, MicOff, X } from "lucide-react";
import { useState } from "react";
import Orb, { type OrbState } from "../brand/Orb";
import Halo from "../shell/Halo";
import { useUi } from "../store/ui";
import { useVoice } from "../store/voice";
import { BOUNCE, GLIDE } from "../ui/motion";
import { type LoopState, useVoiceLoop } from "./loop";

const LABEL: Record<LoopState, string> = {
  listening: "Listening",
  hearing: "Got it",
  thinking: "Thinking",
  speaking: "Tap to interrupt",
  paused: "Mic is off",
};

const ORB: Record<LoopState, OrbState> = {
  listening: "listening",
  hearing: "thinking",
  thinking: "thinking",
  speaking: "speaking",
  paused: "idle",
};

function Round({ label, onClick, danger, children }: { label: string; onClick: () => void; danger?: boolean; children: React.ReactNode }) {
  return (
    <motion.button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      whileTap={{ scale: 0.9 }}
      transition={BOUNCE}
      className={`flex h-16 w-16 items-center justify-center rounded-full shadow-float transition-colors ${
        danger ? "bg-danger text-bg" : "bg-surface text-ink hover:bg-raised"
      }`}
    >
      {children}
    </motion.button>
  );
}

function Loop() {
  const [paused, setPaused] = useState(false);
  const { state, heard, saying, interrupt } = useVoiceLoop(paused);
  const close = () => useUi.getState().setVoiceMode(false);
  return (
    <>
      <button
        type="button"
        onClick={state === "speaking" || state === "thinking" ? interrupt : undefined}
        className="relative flex flex-col items-center outline-none"
        aria-label={LABEL[state]}
      >
        <motion.div animate={{ scale: state === "paused" ? 0.85 : 1 }} transition={BOUNCE}>
          <Orb size={200} state={ORB[state]} />
        </motion.div>
        <p className={`mt-10 text-[17px] font-medium ${state === "thinking" ? "shimmer" : "text-ink-muted"}`}>{LABEL[state]}</p>
      </button>
      <div className="mt-6 min-h-[120px] w-full max-w-2xl px-8 text-center">
        <AnimatePresence mode="wait">
          {saying ? (
            <motion.p key={saying} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={GLIDE} className="font-display text-[24px] leading-snug tracking-tight text-ink">
              {saying}
            </motion.p>
          ) : heard ? (
            <motion.p key={heard} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="text-[18px] text-ink-faint">
              "{heard}"
            </motion.p>
          ) : null}
        </AnimatePresence>
      </div>
      <div className="absolute bottom-12 flex gap-6">
        <Round label={paused ? "Turn the mic on" : "Mute"} onClick={() => setPaused(!paused)}>
          {paused ? <MicOff size={24} strokeWidth={1.75} /> : <Mic size={24} strokeWidth={1.75} />}
        </Round>
        <Round label="End" danger onClick={close}>
          <X size={26} strokeWidth={2} />
        </Round>
      </div>
    </>
  );
}

export default function VoiceMode() {
  const stt = useVoice((s) => s.status?.stt);
  const close = () => useUi.getState().setVoiceMode(false);
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={GLIDE}
      className="fixed inset-0 z-[70] flex flex-col items-center justify-center overflow-hidden bg-bg"
    >
      <Halo state="listening" placement="center" />
      {stt?.available ? (
        <Loop />
      ) : (
        <div className="relative flex max-w-md flex-col items-center px-8 text-center">
          <Orb size={120} />
          <p className="mt-8 text-[20px] font-semibold text-ink">Voice isn't set up on this PC yet</p>
          <p className="mt-2 text-[14.5px] leading-relaxed text-ink-muted">{stt ? `${stt.reason} ${stt.fix}` : "Checking…"}</p>
          <div className="mt-10">
            <Round label="Close" onClick={close}>
              <X size={26} strokeWidth={2} />
            </Round>
          </div>
        </div>
      )}
    </motion.div>
  );
}
