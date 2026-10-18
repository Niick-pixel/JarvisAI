// Home Assistant. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { AssistResult, Device, HomeAction, HomeStatus } from "./types";

export const homeApi = {
  status: () => request<HomeStatus>("/api/home/status"),
  connect: (url: string, token: string) =>
    request<HomeStatus>("/api/home/connection", { method: "PUT", body: JSON.stringify({ url, token }) }),
  disconnect: () => request<HomeStatus>("/api/home/connection", { method: "DELETE" }),
  setRouteChat: (route_chat: boolean) =>
    request<HomeStatus>("/api/home/prefs", { method: "PUT", body: JSON.stringify({ route_chat }) }),
  devices: () => request<Device[]>("/api/home/devices"),
  act: (entity_id: string, action: HomeAction, value?: number) =>
    request<Device[]>("/api/home/action", { method: "POST", body: JSON.stringify({ entity_id, action, value }) }),
  assist: (text: string, conversation_id: string | null = null) =>
    request<AssistResult>("/api/home/assist", { method: "POST", body: JSON.stringify({ text, conversation_id }) }),
};
