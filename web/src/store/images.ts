// Making pictures: whether it is set up, the one in progress, and the "Image" mode of the composer.
import { create } from "zustand";
import { ApiError, request } from "../api/client";
import type { Generated, ImageStatus } from "../api/types";
import { toast } from "./toast";

export const imagesApi = {
  status: () => request<ImageStatus>("/api/images/status"),
  install: (model: string) =>
    request<ImageStatus>("/api/images/install", { method: "POST", body: JSON.stringify({ model }) }),
  generate: (conversation_id: string, prompt: string) =>
    request<Generated>("/api/images/generate", { method: "POST", body: JSON.stringify({ conversation_id, prompt }) }),
};

interface ImagesState {
  status: ImageStatus | null;
  mode: boolean;
  painting: string | null;
  setMode: (on: boolean) => void;
  refresh: () => Promise<void>;
  install: (model: string) => Promise<void>;
  /** Make a picture in this chat. Resolves once it is on disk and linked to its answer. */
  paint: (conversationId: string, prompt: string) => Promise<boolean>;
}

const sleep = (ms: number) => new Promise((done) => setTimeout(done, ms));

export const useImages = create<ImagesState>((set, get) => ({
  status: null,
  mode: false,
  painting: null,

  setMode: (mode) => set({ mode }),

  refresh: async () => set({ status: await imagesApi.status() }),

  install: async (model) => {
    set({ status: await imagesApi.install(model) });
    while (get().status?.state === "installing") {
      await sleep(1000);
      await get().refresh().catch(() => undefined);
    }
  },

  paint: async (conversationId, prompt) => {
    set({ painting: prompt });
    let alive = true;
    void (async () => {
      while (alive) {
        await get().refresh().catch(() => undefined);
        await sleep(700);
      }
    })();
    try {
      await imagesApi.generate(conversationId, prompt);
      return true;
    } catch (error) {
      toast(error instanceof ApiError ? error.body.message : "Couldn't make that picture", "error");
      return false;
    } finally {
      alive = false;
      set({ painting: null });
    }
  },
}));
