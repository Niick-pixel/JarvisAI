// The morning briefing. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { Briefing, BriefingSettings } from "./types";

export const briefingApi = {
  settings: () => request<BriefingSettings>("/api/briefing/settings"),
  save: (body: BriefingSettings) =>
    request<BriefingSettings>("/api/briefing/settings", { method: "PUT", body: JSON.stringify(body) }),
  run: () => request<Briefing>("/api/briefing/run", { method: "POST" }),
  latest: () => request<Briefing | null>("/api/briefing/latest"),
  read: (id: string) => request<null>(`/api/briefing/${id}/read`, { method: "POST" }),
};
