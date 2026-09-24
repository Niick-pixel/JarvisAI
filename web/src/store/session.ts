// One store slice for the conversation and the run attached to it. Kept deliberately small:
// the server owns the truth, this holds what is on screen.
import { create } from "zustand";
import { api } from "../api/client";
import { startChatStream, type ChatRequestBody } from "../api/stream";
import type { ContextAssembly, Conversation, ErrorBody, Message, Remedy, SamplingParams } from "../api/types";
import { useAppearance } from "../design/theme";
import { useLibrary } from "./library";
import { useMemory } from "./memory";
import { thinkingParam, useUi } from "./ui";

export type VisualState = "idle" | "listening" | "thinking" | "streaming" | "error";

interface SessionState {
  conversation: Conversation | null;
  messages: Message[];
  activePath: string[];
  assembly: ContextAssembly | null;
  runId: string | null;
  streamingId: string | null;
  streamingText: string;
  tokenTick: number;
  visual: VisualState;
  error: ErrorBody | null;
  tps: number;

  runStartedAt: number;
  /** How long each answer spent thinking, measured live. Old answers simply do not have one. */
  thoughtMs: Record<string, number>;

  bootstrap: () => Promise<void>;
  newChat: () => void;
  refreshTree: () => Promise<void>;
  openConversation: (id: string) => Promise<void>;
  lastPrompt: string | null;
  research: boolean;
  setResearch: (value: boolean) => void;
  send: (content: string, ctxLen?: number | null) => Promise<void>;
  continueFrom: (messageId: string) => Promise<void>;
  rerun: (messageId: string) => Promise<void>;
  regenerate: (messageId: string) => Promise<void>;
  runStream: (body: ChatRequestBody) => Promise<void>;
  applyRemedy: (remedy: Remedy) => Promise<void>;
  setVisual: (visual: VisualState) => void;
  stop: () => Promise<void>;
  dismissError: () => void;
}

export const useSession = create<SessionState>((set, get) => ({
  conversation: null,
  messages: [],
  activePath: [],
  assembly: null,
  runId: null,
  streamingId: null,
  streamingText: "",
  tokenTick: 0,
  visual: "idle",
  error: null,
  tps: 0,
  lastPrompt: null,
  research: false,
  runStartedAt: 0,
  thoughtMs: {},

  setResearch: (research: boolean) => set({ research }),

  // The app opens on a fresh chat, the way every assistant does. The conversation row is only
  // written when you actually say something, so opening the app never litters the sidebar.
  bootstrap: async () => {
    get().newChat();
  },

  newChat: () => {
    if (get().runId) return;
    set({
      conversation: null,
      messages: [],
      activePath: [],
      assembly: null,
      streamingText: "",
      streamingId: null,
      error: null,
      visual: "idle",
    });
  },

  openConversation: async (id: string) => {
    const tree = await api.tree(id);
    set({
      conversation: tree.conversation,
      messages: tree.messages,
      activePath: tree.active_path,
      assembly: null,
      streamingText: "",
      streamingId: null,
      error: null,
      visual: "idle",
    });
  },

  refreshTree: async () => {
    const conversation = get().conversation;
    if (!conversation) return;
    const tree = await api.tree(conversation.id);
    set({
      conversation: tree.conversation,
      messages: tree.messages,
      activePath: tree.active_path,
    });
  },

  send: async (content: string, ctxLen: number | null = null) => {
    if (get().runId) return;
    let conversation = get().conversation;
    if (!conversation) {
      // The server gives it a real title from the first message; this placeholder never shows.
      conversation = await api.createConversation("New conversation");
      set({ conversation });
    }
    set({ lastPrompt: content });
    await get().runStream({
      conversation_id: conversation.id,
      content,
      ctx_len: ctxLen,
      research: get().research,
      params: { thinking: thinkingParam(useUi.getState().think) } as SamplingParams,
    });
  },

  /** Continue an assistant message you edited: its text becomes the prefix (BRIEF.md 4.1). */
  continueFrom: async (messageId: string) => {
    const conversation = get().conversation;
    if (!conversation || get().runId) return;
    await get().runStream({ conversation_id: conversation.id, continue_from: messageId });
  },

  /** Replay a message with its own recorded seed and params, as a sibling (BRIEF.md 4.5). */
  rerun: async (messageId: string) => {
    const conversation = get().conversation;
    if (!conversation || get().runId) return;
    await get().runStream({ conversation_id: conversation.id, rerun_of: messageId });
  },

  /** A fresh answer to the same question, with a new seed, kept beside the old one. */
  regenerate: async (messageId: string) => {
    const conversation = get().conversation;
    const parent = get().messages.find((m) => m.id === messageId)?.parent_id;
    if (!conversation || !parent || get().runId) return;
    const params = { thinking: thinkingParam(useUi.getState().think) } as SamplingParams;
    await get().runStream({ conversation_id: conversation.id, parent_id: parent, params });
  },

  runStream: async (body) => {
    set({ visual: "thinking", error: null, streamingText: "", assembly: null, runStartedAt: Date.now() });
    await startChatStream(
      body,
      {
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
      },
    );
  },

  stop: async () => {
    const runId = get().runId;
    if (runId) await api.stopRun(runId).catch(() => undefined);
  },

  /** Turn the backend's machine-readable remedy into the one action it describes. */
  applyRemedy: async (remedy: Remedy) => {
    const prompt = get().lastPrompt;
    set({ error: null, visual: "idle" });
    switch (remedy.action) {
      case "enable_performance_mode":
        useAppearance.getState().setReduceEffects(true);
        return;
      case "reduce_context": {
        const ctxLen = Number(remedy.params?.ctx_len ?? 0) || null;
        if (prompt) await get().send(prompt, ctxLen);
        return;
      }
      case "retry":
        if (prompt) await get().send(prompt);
        return;
      case "choose_model":
        return;
    }
  },

  /** Voice claims `listening` while the mic is open; a running generation always outranks it. */
  setVisual: (visual: VisualState) =>
    set((s) => (s.runId && visual !== "error" ? s : { visual })),

  dismissError: () => set({ error: null, visual: "idle" }),
}));
