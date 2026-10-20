// The activity bubble, top right: a small gauge that is always honest about what Jarvis is doing.
// It shows a model load's progress, an answer's speed, or how busy the GPU is - and a red dot
// whenever anything runs in the background. Click it for the full picture: the machine, the
// model, and every job in flight, each with what it is doing right now.
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import type { Activity, HudSample } from "../api/types";
import { headline, useHud, watchHud } from "../store/hud";
import Gauge from "../ui/Gauge";
import { GLIDE } from "../ui/motion";

function gb(mb: number): string {
  return `${(mb / 1024).toFixed(1)} GB`;
}

function Meter({ label, value, detail }: { label: string; value: number | null; detail: string }) {
  return (
    <div className="rounded-2xl bg-ink/[0.04] px-3 py-2.5">
      <span className="block text-[12px] text-ink-faint">{label}</span>
      <span className="block whitespace-nowrap text-[13px] font-semibold tabular-nums text-ink">{detail}</span>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-ink/[0.08]">
        <div className="h-full rounded-full bg-[#E5322D] transition-[width] duration-500" style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }} />
      </div>
    </div>
  );
}

function Job({ job }: { job: Activity }) {
  const pct = job.progress == null ? null : Math.round(job.progress * 100);
  return (
    <li className="py-2">
      <div className="flex items-baseline gap-2">
        <span className="min-w-0 flex-1 truncate text-[13.5px] font-medium text-ink">{job.label}</span>
        <span className="shrink-0 text-[12px] tabular-nums text-ink-faint">
          {pct != null ? `${pct}%` : "working"}
          {job.seconds != null ? ` · ${job.seconds}s` : ""}
        </span>
      </div>
      {job.detail && <p className="truncate text-[12px] text-ink-faint">{job.detail}</p>}
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-ink/[0.08]">
        {pct != null ? (
          <div className="h-full rounded-full bg-accent transition-[width] duration-500" style={{ width: `${pct}%` }} />
        ) : (
          <div className="h-full w-1/3 animate-[slide_1.4s_ease-in-out_infinite] rounded-full bg-accent/70" />
        )}
      </div>
    </li>
  );
}

export function Panel({ sample }: { sample: HudSample | null }) {
  if (!sample) return <p className="py-6 text-center text-[13px] text-ink-faint">Connecting…</p>;
  const gpu = sample.gpu;
  const vram = gpu ? (100 * gpu.vram_used_mb) / gpu.vram_total_mb : null;
  return (
    <>
      <p className="text-[12px] font-medium text-ink-faint">Model</p>
      <p className="mb-3 truncate text-[14px] font-medium text-ink">
        {sample.model ? sample.model.replace(/\.gguf$/i, "") : sample.activity.some((a) => a.kind === "model") ? "Loading…" : "None loaded"}
        {sample.tokens_per_second > 0 && <span className="ml-2 text-[12.5px] font-normal text-ink-faint">{sample.tokens_per_second} tok/s</span>}
      </p>
      <div className="grid grid-cols-2 gap-2">
        {gpu ? (
          <>
            <Meter label="GPU" value={gpu.utilization_pct ?? null} detail={gpu.utilization_pct != null ? `${gpu.utilization_pct}%` : "–"} />
            <Meter label="VRAM" value={vram} detail={`${gb(gpu.vram_used_mb)} / ${gb(gpu.vram_total_mb)}`} />
          </>
        ) : (
          <p className="col-span-2 text-[12.5px] text-ink-faint">No NVIDIA GPU detected - everything runs on the processor.</p>
        )}
        <Meter label="CPU" value={sample.cpu_percent} detail={`${Math.round(sample.cpu_percent)}%`} />
        <Meter label="RAM" value={(100 * sample.ram_used_mb) / sample.ram_total_mb} detail={`${gb(sample.ram_used_mb)} / ${gb(sample.ram_total_mb)}`} />
      </div>
      {gpu?.temperature_c != null && (
        <p className="mt-2 text-[12px] text-ink-faint">
          {gpu.name} · {gpu.temperature_c}°C{gpu.power_w != null ? ` · ${Math.round(gpu.power_w)} W` : ""}
        </p>
      )}
      <p className="mt-4 text-[12px] font-medium text-ink-faint">Running in the background</p>
      {sample.activity.length === 0 ? (
        <p className="py-2 text-[13px] text-ink-muted">Nothing - Jarvis is idle.</p>
      ) : (
        <ul className="divide-y divide-ink/[0.06]">
          {sample.activity.map((job, i) => (
            <Job key={`${job.kind}-${i}`} job={job} />
          ))}
        </ul>
      )}
    </>
  );
}

export default function ActivityBubble() {
  const sample = useHud((s) => s.sample);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => watchHud(), []);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    window.addEventListener("mousedown", away);
    return () => window.removeEventListener("mousedown", away);
  }, [open]);
  const head = headline(sample);

  return (
    <div ref={box} className="relative ml-auto">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-label="System and background activity"
        title={`${head.text} ${head.unit}`.trim()}
        className="flex h-11 w-11 items-center justify-center rounded-full transition-colors hover:bg-ink/[0.06]"
      >
        <Gauge value={head.value} text={head.text} busy={head.busy} size={34} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4 }}
            transition={GLIDE}
            className="absolute right-0 top-12 z-50 w-80 rounded-3xl border border-ink/[0.07] bg-surface p-4 shadow-float"
          >
            <div className="mb-3 flex items-center gap-4">
              <Gauge value={head.value} text={head.text} unit={head.unit} busy={head.busy} size={64} />
              <div>
                <p className="text-[15px] font-semibold text-ink">Activity</p>
                <p className="text-[12.5px] text-ink-faint">Live, once a second. Nothing is hidden.</p>
              </div>
            </div>
            <Panel sample={sample} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
