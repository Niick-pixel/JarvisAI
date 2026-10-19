// The wake word: whether it is on (remembered on this PC), whether its models are here, and
// whether the microphone is open for it right now.
import { create } from "zustand";
import { wakeApi } from "../voice/wake";

const KEY = "jarvis.wake";

function loadEnabled(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

interface WakeState {
  enabled: boolean;
  installing: boolean;
  listening: boolean;
  error: string;
  setEnabled: (on: boolean) => Promise<void>;
  setListening: (on: boolean) => void;
  setError: (message: string) => void;
}

export const useWake = create<WakeState>((set) => ({
  enabled: loadEnabled(),
  installing: false,
  listening: false,
  error: "",

  setEnabled: async (on) => {
    set({ error: "" });
    if (on && !(await wakeApi.status()).installed) {
      set({ installing: true });
      try {
        await wakeApi.install();
      } catch (error) {
        set({ error: error instanceof Error ? error.message : String(error) });
        return;
      } finally {
        set({ installing: false });
      }
    }
    set({ enabled: on });
    try {
      localStorage.setItem(KEY, on ? "1" : "0");
    } catch {
      // A convenience; turning it on again is one click.
    }
  },
  setListening: (listening) => set({ listening }),
  setError: (error) => set({ error }),
}));
