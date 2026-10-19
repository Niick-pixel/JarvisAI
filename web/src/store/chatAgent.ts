// Agent mode in chat: a turn that may use tools. The server drives the loop; this follows it -
// attaching to each generation as it streams and surfacing every call that waits for you.
import { create } from "zustand";
import { api } from "../api/client";
import { chatAgentApi } from "../api/chatAgent";
import { resumeRun } from "../api/stream";
import type { PendingCall, SamplingParams } from "../api/types";
import { useLibrary } from "./library";
import { useSession } from "./session";
import { streamHandlers } from "./streamHandlers";
import { useCode } from "./code";

interface ChatAgentState {
  /** The agent turn running in this chat, if any. */
  runId: string | null;
  calls: PendingCall[];
  busy: string | null;
  start: (conversationId: string, content: string, params: SamplingParams) => Promise<void>;
  decide: (callId: string, approve: boolean, grant: boolean) => Promise<void>;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const useChatAgent = create<ChatAgentState>((set, get) => ({
  runId: null,
  calls: [],
  busy: null,

  start: async (conversationId, content, params) => {
    const session = useSession;
    session.setState({ visual: "thinking", error: null, streamingText: "", assembly: null, runStartedAt: Date.now() });
    let runId: string;
    try {
      // Code mode: the tools work in your project folder, with a coder model when there is one.
      const code = useCode.getState();
      const extra = code.on && code.project ? { project: code.project, model_id: code.coder() } : undefined;
      runId = (await chatAgentApi.start(conversationId, content, params, extra)).run_id;
    } catch {
      session.setState({ visual: "idle" });
      return;
    }
    set({ runId, calls: [] });
    let attached = "";
    let closing: Promise<void> | null = null;
    for (;;) {
      const turn = await chatAgentApi.turn(runId).catch(() => null);
      if (!turn) break;
      set({ calls: turn.calls });
      if (turn.live_run_id && turn.live_run_id !== attached) {
        // A new generation: stream it into the chat exactly like an ordinary answer.
        attached = turn.live_run_id;
        session.setState({ runStartedAt: Date.now(), streamingText: "" });
        closing = new Promise((resolve) => {
          const handlers = streamHandlers(session.getState, session.setState);
          resumeRun(attached, {
            ...handlers,
            onClose: async () => {
              await handlers.onClose();
              resolve();
            },
          });
        });
      }
      if (turn.status === "done" || turn.status === "failed" || turn.status === "cancelled") {
        await closing;
        if (turn.error) session.setState({ error: { code: "internal", message: turn.error }, visual: "error" });
        break;
      }
      if (!turn.live_run_id) {
        // Between generations - a tool ran, or a call waits for you. Keep the thread current.
        await session.getState().refreshTree().catch(() => undefined);
        if (session.getState().visual === "idle") session.setState({ visual: "thinking" });
      }
      await sleep(turn.status === "waiting_approval" ? 700 : 350);
    }
    await session.getState().refreshTree().catch(() => undefined);
    void useLibrary.getState().refresh().catch(() => undefined);
    session.setState((s) => ({ visual: s.visual === "error" ? "error" : "idle" }));
    set({ runId: null, calls: get().calls.filter((c) => c.status !== "pending") });
  },

  decide: async (callId, approve, grant) => {
    set({ busy: callId });
    try {
      await api.decideCall(callId, { approve, grant });
      set((s) => ({ calls: s.calls.map((c) => (c.id === callId ? { ...c, status: approve ? "approved" : "denied" } : c)) }));
    } finally {
      set({ busy: null });
    }
  },
}));
