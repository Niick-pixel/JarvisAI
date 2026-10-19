// The trading co-pilot. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { AlertRule, AlertRuleCreate, JournalAnswer, JournalImport, JournalStats, LiveStatus, Trade } from "./types";

export const NINJASCRIPT_URL = "/api/trading/ninjascript";

export const tradingApi = {
  live: () => request<LiveStatus>("/api/trading/live"),
  rules: () => request<AlertRule[]>("/api/trading/alerts"),
  addRule: (body: AlertRuleCreate) =>
    request<AlertRule>("/api/trading/alerts", { method: "POST", body: JSON.stringify(body) }),
  removeRule: (id: string) => request<null>(`/api/trading/alerts/${id}`, { method: "DELETE" }),
  readEvents: () => request<null>("/api/trading/alerts/events/read", { method: "POST" }),
  journal: () => request<JournalStats>("/api/trading/journal"),
  trades: () => request<Trade[]>("/api/trading/journal/trades?limit=12"),
  importJournal: (text: string) =>
    request<JournalImport>("/api/trading/journal/import", { method: "POST", body: text }),
  clearJournal: () => request<null>("/api/trading/journal", { method: "DELETE" }),
  ask: (question: string) =>
    request<JournalAnswer>("/api/trading/journal/ask", { method: "POST", body: JSON.stringify({ question }) }),
};
