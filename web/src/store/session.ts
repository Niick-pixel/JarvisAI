// One store slice for the conversation and the run attached to it. Kept deliberately small:
// the server owns the truth, this holds what is on screen.
import { create } from "zustand";
import { api } from "../api/client";
import { chatAgentApi } from "../api/chatAgent";
import { homeApi } from "../api/home";
import { startChatStream, type ChatRequestBody } from "../api/stream";
import type { ContextAssembly, Conversation, ErrorBody, Message, Remedy, SamplingParams } from "../api/types";
import { useAppearance } from "../design/theme";
import { useChatAgent } from "./chatAgent";
import { streamHandlers } from "./streamHandlers";
import { thinkingParams, useUi } from "./ui";

export type VisualState = "idle" | "listening" | "thinking" | "streaming" | "error";

export interface SessionState {
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
  /** Agent mode: the model may use tools in this answer, each one under your approval. */
  tools: boolean;
  setTools: (value: boolean) => void;
  send: (content: string, ctxLen?: number | null) => Promise<void>;
  /** The last reply Home Assistant gave in this chat, so voice mode can read it out. */
  homeReply: { at: number; text: string } | null;
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
  tools: false,
  runStartedAt: 0,
  thoughtMs: {},
  homeReply: null,

  setResearch: (research: boolean) => set({ research }),
  setTools: (tools: boolean) => set({ tools }),

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
    if (get().runId || useChatAgent.getState().runId) return;
    let conversation = get().conversation;
    if (!conversation) {
      // The server gives it a real title from the first message; this placeholder never shows.
      conversation = await api.createConversation("New conversation");
      set({ conversation });
    }
    set({ lastPrompt: content });
    // Home Assistant's own matcher gets the first look: "turn off the kitchen lights" is done by
    // it and written into this chat, anything else falls through to the model untouched.
    const home = await homeApi.assist(content, conversation.id).catch(() => null);
    if (home?.handled) {
      await get().refreshTree();
      set({ homeReply: { at: Date.now(), text: home.reply } });
      return;
    }
    const params = thinkingParams(useUi.getState().think) as SamplingParams;
    if (get().tools) {
      await useChatAgent.getState().start(conversation.id, content, params);
      return;
    }
    await get().runStream({
      conversation_id: conversation.id,
      content,
      ctx_len: ctxLen,
      research: get().research,
      params,
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
    const params = thinkingParams(useUi.getState().think) as SamplingParams;
    await get().runStream({ conversation_id: conversation.id, parent_id: parent, params });
  },

  runStream: async (body) => {
    set({ visual: "thinking", error: null, streamingText: "", assembly: null, runStartedAt: Date.now() });
    await startChatStream(body, streamHandlers(get, set));
  },

  stop: async () => {
    const agentRun = useChatAgent.getState().runId;
    if (agentRun) await chatAgentApi.stop(agentRun).catch(() => undefined);
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
