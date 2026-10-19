// Workflows by example: the draft being reviewed, and how each workflow has been doing.
import { create } from "zustand";
import { workflowsApi } from "../api/workflows";
import type { JobDraft, JobStats } from "../api/types";
import { useUi } from "./ui";

interface WorkflowsState {
  draft: JobDraft | null;
  drafting: boolean;
  stats: Record<string, JobStats>;
  describe: (text: string) => Promise<void>;
  /** "Make this a workflow": draft from a chat, then open the form to review it. */
  fromChat: (conversationId: string) => Promise<void>;
  clear: () => void;
  loadStats: () => Promise<void>;
}

export const useWorkflows = create<WorkflowsState>((set) => ({
  draft: null,
  drafting: false,
  stats: {},

  describe: async (text) => {
    set({ drafting: true });
    try {
      set({ draft: await workflowsApi.draft(text) });
    } finally {
      set({ drafting: false });
    }
  },

  fromChat: async (conversationId) => {
    set({ drafting: true, draft: null });
    useUi.setState({ sheet: "agents" });
    try {
      set({ draft: await workflowsApi.fromChat(conversationId) });
    } finally {
      set({ drafting: false });
    }
  },

  clear: () => set({ draft: null }),

  loadStats: async () => {
    const rows = await workflowsApi.dashboard();
    set({ stats: Object.fromEntries(rows.map((r) => [r.job_id, r])) });
  },
}));
