// The memory timeline. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { MemoryEntry, MemoryUse } from "./types";

export const memoryApi = {
  uses: (id: string) => request<MemoryUse[]>(`/api/memory/${id}/uses`),
  forgetChat: (conversationId: string) =>
    request<MemoryEntry[]>(`/api/memory/from-conversation/${conversationId}`, { method: "DELETE" }),
  restore: (entries: MemoryEntry[]) =>
    request<{ remaining: number }>("/api/memory/restore", { method: "POST", body: JSON.stringify(entries) }),
};
