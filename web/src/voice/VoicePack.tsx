// "Get voice": downloads the model that listens and the voice that speaks, with a real progress
// bar, from Settings or from voice mode itself. Nothing is fetched until it is pressed.
import { motion } from "framer-motion";
import { AudioLines } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { VoicePackProgress } from "../api/types";
import { useVoice } from "../store/voice";
import { Button } from "../ui/controls";
import { GLIDE } from "../ui/motion";

const ACTIVE = ["downloading", "verifying"];

function mb(bytes: number): string {
  return `${Math.round(bytes / 1e6).toLocaleString()} MB`;
}

export default function VoicePack() {
  const [progress, setProgress] = useState<VoicePackProgress | null>(null);
  const status = useVoice((s) => s.status);
  const active = ACTIVE.includes(progress?.state ?? "");

  useEffect(() => {
    void api.voicePack().then(setProgress).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      void api
        .voicePack()
        .then((next) => {
          setProgress(next);
          if (next.state === "done") void useVoice.getState().refresh();
        })
        .catch(() => undefined);
    }, 700);
    return () => window.clearInterval(timer);
  }, [active]);

  const downloadable = status?.stt.downloadable || status?.tts.downloadable;
  if (!downloadable && !active) return null;
  const fraction = progress?.bytes_total ? progress.bytes_done / progress.bytes_total : 0;

  if (active && progress) {
    return (
      <div className="w-full rounded-3xl bg-accent/[0.07] p-4 text-left">
        <div className="flex items-center gap-3">
          <p className="min-w-0 flex-1 text-[14px] text-ink">
            Getting voice… {progress.bytes_total ? `${mb(progress.bytes_done)} of ${mb(progress.bytes_total)}` : ""}
          </p>
          <Button small tone="ghost" onClick={() => void api.cancelVoicePack().then(setProgress)}>
            Pause
          </Button>
        </div>
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink/[0.07]">
          <motion.div className="h-full rounded-full bg-accent" animate={{ width: `${fraction * 100}%` }} transition={GLIDE} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <Button tone="primary" icon={AudioLines} onClick={() => void api.startVoicePack().then(setProgress)}>
        {progress?.state === "failed" || progress?.state === "cancelled" ? "Resume download" : "Get voice"}
      </Button>
      {progress?.state === "failed" && <p className="text-[12.5px] text-danger">{progress.detail}</p>}
    </div>
  );
}
