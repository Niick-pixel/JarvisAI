// The tile shown on the desktop while Jarvis is minimised (server/desktop_widget.py): the same
// gauge as the activity bubble, what it measures, and the one thing running. Click to go back.
import { useEffect } from "react";
import { headline, useHud, watchHud } from "../store/hud";
import Gauge from "../ui/Gauge";

interface Desktop {
  pywebview?: { api?: { restore_main?: () => Promise<void> } };
}

export default function MiniWidget() {
  const sample = useHud((s) => s.sample);
  useEffect(() => watchHud(), []);
  const head = headline(sample);
  const job = sample?.activity[0];
  return (
    <button
      type="button"
      onClick={() => void (window as unknown as Desktop).pywebview?.api?.restore_main?.()}
      title={job ? job.label : "Open Jarvis"}
      className="pywebview-drag-region flex h-screen w-screen flex-col items-center justify-center gap-1 rounded-3xl bg-[#16181D] text-white"
    >
      <Gauge value={head.value} text={head.text} unit={head.unit} busy={head.busy} size={84} onDark />
      <span className="max-w-[112px] truncate text-[10px] text-white/60">{job ? job.label.replace(/\.gguf$/i, "") : "Idle"}</span>
    </button>
  );
}
