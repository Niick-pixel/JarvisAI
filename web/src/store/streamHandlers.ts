// What a chat stream does to the session as its events arrive: the run starting, each token, the
// end. Its own module so session.ts stays readable.
import type { StreamHandlers } from "../api/stream";
import { useLibrary } from "./library";
import { useMemory } from "./memory";
import type { SessionState } from "./session";

type Get = () => SessionState;
type Set = (next: Partial<SessionState> | ((s: SessionState) => Partial<SessionState>)) => void;

export function streamHandlers(get: Get, set: Set): StreamHandlers {
  return {
    onEvent: (event) => {
      switch (event.type) {
        case "assembly":
          set({ assembly: event.assembly });
          break;
        case "run":
          set({ runId: event.run_id, streamingId: event.message_id, visual: "streaming" });
          // The user turn and the assistant row both exist on the server by now. Pull them
          // rather than inventing local ids, so what is on screen is what is on disk.
          void get()
            .refreshTree()
            .catch(() => undefined);
          // The first message gave the chat a title; show it in the sidebar straight away.
          void useLibrary.getState().refresh().catch(() => undefined);
          break;
        case "token":
          set((s) => {
            const streamingText = s.streamingText + event.text;
            const id = s.streamingId;
            const thoughtMs =
              id && !(id in s.thoughtMs) && streamingText.includes("</think>")
                ? { ...s.thoughtMs, [id]: Date.now() - s.runStartedAt }
                : s.thoughtMs;
            return { streamingText, thoughtMs, tokenTick: s.tokenTick + 1 };
          });
          break;
        case "usage":
          set({ tps: event.tps });
          break;
        case "error":
          set({ error: event.error, visual: "error" });
          break;
        case "done":
          break;
      }
    },
    onFailure: (error) => set({ error, visual: "error" }),
    onClose: async () => {
      await get().refreshTree().catch(() => undefined);
      const finished = get().streamingId;
      if (finished) {
        // Capture also refines the chat's title, so the sidebar is refreshed once it is done.
        void useMemory
          .getState()
          .awaitCapture(finished)
          .catch(() => undefined)
          .finally(() => void useLibrary.getState().refresh().catch(() => undefined));
      }
      set((s) => ({
        runId: null,
        streamingId: null,
        streamingText: "",
        visual: s.visual === "error" ? "error" : "idle",
      }));
    },
  };
}
