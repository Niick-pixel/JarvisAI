// What is open, what is collapsed, and how you like to be answered. The layout's state, kept in
// one place so there is only ever one sheet on screen - never two panels fighting for the side.
import { create } from "zustand";

export type SheetName = "memory" | "knowledge" | "agents" | "settings" | "council";

/** "auto" lets the model decide; "on"/"off" ask a reasoning model to think first or not. */
export type ThinkMode = "auto" | "on" | "off";

const KEY = "jarvis.ui";

interface Stored {
  sidebarOpen: boolean;
  think: ThinkMode;
  name: string;
  /** Shows the context meter at all times, and the performance readout. */
  devTools: boolean;
}

function load(): Stored {
  const fallback: Stored = { sidebarOpen: true, think: "auto", name: "", devTools: false };
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { ...fallback, ...(JSON.parse(raw) as Partial<Stored>) };
  } catch {
    // Blocked storage must never stop the app from starting.
  }
  return fallback;
}

interface UiState extends Stored {
  sheet: SheetName | null;
  voiceMode: boolean;
  openSheet: (sheet: SheetName) => void;
  closeSheet: () => void;
  toggleSidebar: () => void;
  setThink: (think: ThinkMode) => void;
  setName: (name: string) => void;
  setVoiceMode: (on: boolean) => void;
  setDevTools: (on: boolean) => void;
}

export const useUi = create<UiState>((set, get) => ({
  ...load(),
  sheet: null,
  voiceMode: false,
  // Opening a sheet replaces whatever was open; tapping the same one again closes it.
  openSheet: (sheet) => set((s) => ({ sheet: s.sheet === sheet ? null : sheet })),
  closeSheet: () => set({ sheet: null }),
  toggleSidebar: () => {
    set((s) => ({ sidebarOpen: !s.sidebarOpen }));
    persist(get());
  },
  setThink: (think) => {
    set({ think });
    persist(get());
  },
  setName: (name) => {
    set({ name });
    persist(get());
  },
  setVoiceMode: (voiceMode) => set({ voiceMode, sheet: null }),
  setDevTools: (devTools) => {
    set({ devTools });
    persist(get());
  },
}));

/** What the think toggle sends: null leaves it to the model and its template. */
export function thinkingParam(think: ThinkMode): boolean | null {
  return think === "auto" ? null : think === "on";
}

function persist(state: Stored): void {
  try {
    localStorage.setItem(
      KEY,
      JSON.stringify({
        sidebarOpen: state.sidebarOpen,
        think: state.think,
        name: state.name,
        devTools: state.devTools,
      }),
    );
  } catch {
    // Nothing here is worth failing over.
  }
}
