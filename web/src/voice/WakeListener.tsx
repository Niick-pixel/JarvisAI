// "Hey Jarvis" starts voice mode. The microphone is open only while the wake word is on, voice
// mode is not already running, and the window is visible - and while it is open, a badge says so.
import { Ear } from "lucide-react";
import { useEffect } from "react";
import { useUi } from "../store/ui";
import { useWake } from "../store/wake";
import { listen } from "./wake";

export default function WakeListener() {
  const enabled = useWake((s) => s.enabled);
  const listening = useWake((s) => s.listening);
  const voiceMode = useUi((s) => s.voiceMode);

  useEffect(() => {
    if (!enabled || voiceMode) return;
    let ear: { stop: () => void } | null = null;
    let cancelled = false;
    const { setListening, setError } = useWake.getState();
    listen(
      () => useUi.getState().setVoiceMode(true),
      (message) => {
        setListening(false);
        setError(message);
      },
    )
      .then((opened) => {
        if (cancelled) return opened.stop();
        ear = opened;
        setListening(true);
      })
      .catch((error: unknown) => setError(error instanceof Error ? error.message : String(error)));
    return () => {
      cancelled = true;
      ear?.stop();
      setListening(false);
    };
  }, [enabled, voiceMode]);

  if (!listening) return null;
  return (
    <div
      className="pointer-events-none fixed right-4 top-3 z-40 inline-flex items-center gap-1.5 rounded-full bg-surface/80 px-3 py-1.5 text-[12px] font-medium text-ink-muted shadow-card backdrop-blur"
      title="The microphone is on, listening only for the wake word, on this PC"
    >
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
      <Ear size={13} strokeWidth={2} />
      Listening for "Hey Jarvis"
    </div>
  );
}
