// Workflows by example. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { JobDraft, JobStats } from "./types";

export const workflowsApi = {
  draft: (description: string) =>
    request<JobDraft>("/api/agents/drafts", { method: "POST", body: JSON.stringify({ description }) }),
  fromChat: (conversationId: string) =>
    request<JobDraft>(`/api/agents/drafts/from-conversation/${conversationId}`, { method: "POST" }),
  dashboard: () => request<JobStats[]>("/api/agents/dashboard"),
};
