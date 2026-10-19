// The trading co-pilot: the live feed, alert rules, and the trade journal.
import { create } from "zustand";
import { ApiError } from "../api/client";
import { tradingApi } from "../api/trading";
import type { AlertRule, AlertRuleCreate, JournalAnswer, JournalStats, LiveStatus, Trade } from "../api/types";

const SPEAK_KEY = "jarvis.speakAlerts";

function loadSpeak(): boolean {
  try {
    return localStorage.getItem(SPEAK_KEY) === "1";
  } catch {
    return false;
  }
}

const message = (error: unknown) => (error instanceof ApiError ? error.body.message : String(error));

interface TradingState {
  live: LiveStatus | null;
  rules: AlertRule[];
  stats: JournalStats | null;
  trades: Trade[];
  answer: JournalAnswer | null;
  asking: boolean;
  note: string;
  speakAlerts: boolean;
  refreshLive: () => Promise<void>;
  refreshAll: () => Promise<void>;
  addRule: (body: AlertRuleCreate) => Promise<void>;
  removeRule: (id: string) => Promise<void>;
  importJournal: (files: File[]) => Promise<void>;
  clearJournal: () => Promise<void>;
  ask: (question: string) => Promise<void>;
  setSpeakAlerts: (on: boolean) => void;
}

export const useTrading = create<TradingState>((set, get) => ({
  live: null,
  rules: [],
  stats: null,
  trades: [],
  answer: null,
  asking: false,
  note: "",
  speakAlerts: loadSpeak(),

  refreshLive: async () => set({ live: await tradingApi.live() }),

  refreshAll: async () => {
    const [live, rules, stats, trades] = await Promise.all([
      tradingApi.live(),
      tradingApi.rules(),
      tradingApi.journal(),
      tradingApi.trades(),
    ]);
    set({ live, rules, stats, trades });
  },

  addRule: async (body) => {
    await tradingApi.addRule(body);
    set({ rules: await tradingApi.rules() });
  },

  removeRule: async (id) => {
    await tradingApi.removeRule(id);
    set({ rules: await tradingApi.rules() });
  },

  importJournal: async (files) => {
    const notes: string[] = [];
    for (const file of files) {
      try {
        const result = await tradingApi.importJournal(await file.text());
        notes.push(
          `${file.name}: ${result.added} new trade${result.added === 1 ? "" : "s"}` +
            (result.skipped ? `, ${result.skipped} already in your journal` : "") +
            (result.unreadable ? `, ${result.unreadable} rows could not be read` : ""),
        );
      } catch (error) {
        notes.push(`${file.name}: ${message(error)}`);
      }
    }
    set({ note: notes.join(" · ") });
    await get().refreshAll();
  },

  clearJournal: async () => {
    await tradingApi.clearJournal();
    set({ answer: null, note: "" });
    await get().refreshAll();
  },

  ask: async (question) => {
    set({ asking: true, answer: null });
    try {
      set({ answer: await tradingApi.ask(question) });
    } catch (error) {
      set({ answer: { answer: message(error), model_id: null } });
    } finally {
      set({ asking: false });
    }
  },

  setSpeakAlerts: (on) => {
    set({ speakAlerts: on });
    try {
      localStorage.setItem(SPEAK_KEY, on ? "1" : "0");
    } catch {
      // A convenience, not state that must survive.
    }
  },
}));
