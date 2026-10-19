// What Jarvis sees while you share your screen: a live thumbnail, a red dot, and Stop. Refreshed
// once a second while the window is visible; the frames are shown, never stored.
import { MonitorUp, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useScreenShare } from "../store/screenShare";
import { whenVisible } from "../ui/visible";

export default function SharePill() {
  const { on, stop } = useScreenShare();
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!on) return;
    const timer = window.setInterval(
      whenVisible(() => setTick((t) => t + 1)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [on]);
  if (!on) return null;
  return (
    <div className="mb-2 flex items-center gap-3 rounded-2xl border border-ink/[0.08] bg-surface/80 p-2 pr-3 backdrop-blur">
      <img
        src={`/api/screen/frame?size=240&t=${tick}`}
        alt="Your screen, as Jarvis sees it"
        className="h-12 w-20 shrink-0 rounded-lg bg-ink/[0.05] object-cover"
      />
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-2 text-[13.5px] font-medium text-ink">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-danger opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-danger" />
          </span>
          <MonitorUp size={15} /> Sharing your screen
        </p>
        <p className="truncate text-[12.5px] text-ink-faint">
          Each message you send - typed or spoken - includes what's on it.
        </p>
      </div>
      <button
        type="button"
        onClick={stop}
        className="inline-flex h-8 items-center gap-1 rounded-full px-3 text-[13px] font-medium text-danger hover:bg-danger/10"
      >
        <X size={15} /> Stop
      </button>
    </div>
  );
}
