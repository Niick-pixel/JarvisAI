// Memory: the facts on disk, and the batch the last turn just wrote.
import { create } from "zustand";
import { api } from "../api/client";
import { memoryApi } from "../api/memory";
import type { MemoryBatch, MemoryEntry } from "../api/types";

interface MemoryState {
  entries: MemoryEntry[];
  lastCapture: MemoryBatch | null;
  loading: boolean;

  refresh: () => Promise<void>;
  add: (title: string, content: string, always: boolean) => Promise<void>;
  edit: (id: string, patch: { title?: string; content?: string; always?: boolean }) => Promise<void>;
  forget: (id: string) => Promise<void>;
  /** Forget everything one chat taught. */
  forgetChat: (conversationId: string) => Promise<void>;
  /** What the last forget removed, kept just long enough to undo it. */
  forgotten: MemoryEntry[] | null;
  undoForget: () => Promise<void>;
  awaitCapture: (messageId: string) => Promise<void>;
  undoCapture: () => Promise<void>;
  dismissCapture: () => void;
}

export const useMemory = create<MemoryState>((set, get) => ({
  entries: [],
  lastCapture: null,
  loading: false,
  forgotten: null,

  refresh: async () => {
    set({ loading: true });
    try {
      set({ entries: await api.memory() });
    } finally {
      set({ loading: false });
    }
  },

  add: async (title, content, always) => {
    await api.createMemory({ title, content, always });
    await get().refresh();
  },

  edit: async (id, patch) => {
    await api.updateMemory(id, patch);
    await get().refresh();
  },

  /** A hard delete: the Markdown file is removed and the index rebuilt. */
  forget: async (id) => {
    const entry = get().entries.find((e) => e.id === id);
    await api.forgetMemory(id);
    set({ forgotten: entry ? [entry] : null });
    await get().refresh();
  },

  forgetChat: async (conversationId) => {
    const gone = await memoryApi.forgetChat(conversationId);
    set({ forgotten: gone.length ? gone : null });
    await get().refresh();
  },

  undoForget: async () => {
    const back = get().forgotten;
    set({ forgotten: null });
    if (back) await memoryApi.restore(back);
    await get().refresh();
  },

  /** Wait for the capture this turn caused, so the toast reports fact rather than guesswork. */
  awaitCapture: async (messageId) => {
    const batch = await api.captureFor(messageId);
    if (batch.entries.length > 0) {
      set({ lastCapture: batch });
      await get().refresh();
    }
  },

  undoCapture: async () => {
    const batch = get().lastCapture;
    if (!batch) return;
    set({ lastCapture: null });
    await api.undoCapture(batch.batch_id);
    await get().refresh();
  },

  dismissCapture: () => set({ lastCapture: null }),
}));
