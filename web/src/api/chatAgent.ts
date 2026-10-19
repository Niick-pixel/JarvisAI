// Agent mode in chat. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { AgentTurn, AgentTurnStarted, SamplingParams } from "./types";

export const chatAgentApi = {
  start: (conversation_id: string, content: string, params: SamplingParams) =>
    request<AgentTurnStarted>("/api/chat/agent", {
      method: "POST",
      body: JSON.stringify({ conversation_id, content, params }),
    }),
  stop: (runId: string) => request<AgentTurnStarted>(`/api/chat/agent/${runId}/stop`, { method: "POST" }),
  turn: (runId: string) => request<AgentTurn>(`/api/chat/agent/${runId}`),
};
