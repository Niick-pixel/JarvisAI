// The library: every conversation saved on this machine, and every model this machine can reach.
// Kept apart from session.ts, which owns the one conversation currently on screen.
import { create } from "zustand";
import { api } from "../api/client";
import type { Conversation, ModelOption } from "../api/types";
import { useSession } from "./session";

interface LibraryState {
  conversations: Conversation[];
  models: ModelOption[];
  selectedModelId: string | null;
  loading: boolean;

  refresh: () => Promise<void>;
  refreshModels: () => Promise<void>;
  open: (id: string) => Promise<void>;
  create: () => Promise<void>;
  remove: (id: string) => Promise<void>;
  selectModel: (id: string | null) => Promise<void>;
}

export const useLibrary = create<LibraryState>((set, get) => ({
  conversations: [],
  models: [],
  selectedModelId: null,
  loading: false,

  refresh: async () => {
    set({ conversations: await api.listConversations() });
  },

  refreshModels: async () => {
    set({ loading: true });
    try {
      const [models, selected] = await Promise.all([api.modelOptions(), api.selectedModel()]);
      set({ models, selectedModelId: selected.model_id ?? null });
    } finally {
      set({ loading: false });
    }
  },

  open: async (id: string) => {
    await useSession.getState().openConversation(id);
    await get().refresh();
  },

  create: async () => {
    useSession.getState().newChat();
  },

  remove: async (id: string) => {
    await api.deleteConversation(id);
    await get().refresh();
    // Deleting the conversation you were reading should land you somewhere, not nowhere.
    if (useSession.getState().conversation?.id === id) useSession.getState().newChat();
  },

  selectModel: async (id: string | null) => {
    const result = await api.selectModel(id);
    set({ selectedModelId: result.model_id ?? null });
  },
}));
