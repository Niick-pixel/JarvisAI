// The morning briefing: its schedule, and the latest one written.
import { create } from "zustand";
import { briefingApi } from "../api/briefing";
import type { Briefing, BriefingSettings } from "../api/types";

interface BriefingState {
  latest: Briefing | null;
  settings: BriefingSettings | null;
  running: boolean;
  load: () => Promise<void>;
  run: () => Promise<void>;
  save: (patch: Partial<BriefingSettings>) => Promise<void>;
  markRead: () => Promise<void>;
}

export const useBriefing = create<BriefingState>((set, get) => ({
  latest: null,
  settings: null,
  running: false,

  load: async () => {
    const [latest, settings] = await Promise.all([briefingApi.latest(), briefingApi.settings()]);
    set({ latest, settings });
  },

  run: async () => {
    set({ running: true });
    try {
      set({ latest: await briefingApi.run() });
    } finally {
      set({ running: false });
    }
  },

  save: async (patch) => {
    const current = get().settings;
    if (!current) return;
    set({ settings: { ...current, ...patch } });
    set({ settings: await briefingApi.save({ ...current, ...patch }) });
  },

  markRead: async () => {
    const latest = get().latest;
    if (!latest || latest.read_at) return;
    set({ latest: { ...latest, read_at: Date.now() } });
    await briefingApi.read(latest.id).catch(() => undefined);
  },
}));
