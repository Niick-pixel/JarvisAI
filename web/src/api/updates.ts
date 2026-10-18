// New versions of the app. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { UpdateStatus } from "./types";

export const updatesApi = {
  status: () => request<UpdateStatus>("/api/updates"),
  check: () => request<UpdateStatus>("/api/updates/check", { method: "POST" }),
  download: () => request<UpdateStatus>("/api/updates/download", { method: "POST" }),
  install: () => request<UpdateStatus>("/api/updates/install", { method: "POST" }),
  setAuto: (auto: boolean) =>
    request<UpdateStatus>("/api/updates/prefs", { method: "PUT", body: JSON.stringify({ auto }) }),
};
