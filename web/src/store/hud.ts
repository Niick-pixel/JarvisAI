// The machine, the model and every background job, once a second from /api/hud/stream. One stream
// for the whole window, opened while something is watching and closed while the window is hidden.
import { create } from "zustand";
import type { HudSample } from "../api/types";

interface HudState {
  sample: HudSample | null;
  connected: boolean;
}

export const useHud = create<HudState>(() => ({ sample: null, connected: false }));

let source: EventSource | null = null;
let watchers = 0;

function open() {
  if (source || document.visibilityState === "hidden") return;
  source = new EventSource("/api/hud/stream");
  source.addEventListener("hud", (event) => {
    useHud.setState({ sample: JSON.parse((event as MessageEvent<string>).data) as HudSample, connected: true });
  });
  source.onerror = () => useHud.setState({ connected: false });
}

function close() {
  source?.close();
  source = null;
}

const onVisibility = () => (document.visibilityState === "hidden" ? close() : watchers > 0 && open());

/** Start receiving samples; returns the stop function. Safe to call from several components. */
export function watchHud(): () => void {
  watchers += 1;
  if (watchers === 1) document.addEventListener("visibilitychange", onVisibility);
  open();
  return () => {
    watchers -= 1;
    if (watchers === 0) {
      document.removeEventListener("visibilitychange", onVisibility);
      close();
    }
  };
}

/** What the gauge shows: a load's progress, the answer's speed, or how busy the GPU (or CPU) is. */
export function headline(sample: HudSample | null): { value: number; text: string; unit: string; busy: boolean } {
  if (!sample) return { value: 0, text: "–", unit: "", busy: false };
  const loading = sample.activity.find((a) => a.kind === "model");
  if (loading) {
    const pct = Math.round((loading.progress ?? 0) * 100);
    return { value: pct, text: loading.progress == null ? "…" : `${pct}`, unit: "load", busy: true };
  }
  if (sample.tokens_per_second > 0) {
    return { value: Math.min(100, sample.tokens_per_second * 2), text: `${Math.round(sample.tokens_per_second)}`, unit: "tok/s", busy: true };
  }
  const gpu = sample.gpu?.utilization_pct;
  const value = gpu ?? Math.round(sample.cpu_percent);
  return { value, text: `${value}`, unit: gpu != null ? "GPU" : "CPU", busy: sample.activity.length > 0 };
}
