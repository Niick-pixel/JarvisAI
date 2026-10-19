// Files. Kept beside client.ts rather than in it, which is long enough.
import { request } from "./client";
import type { FileContent, FileEntry, FileRoot, Proposal, RunResult } from "./types";

const q = (params: Record<string, string>) => new URLSearchParams(params).toString();
const post = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const filesApi = {
  roots: () => request<FileRoot[]>("/api/files/roots"),
  addRoot: (path: string) => request<FileRoot>("/api/files/roots", post({ path })),
  removeRoot: (id: string) => request<FileRoot[]>(`/api/files/roots/${id}`, { method: "DELETE" }),
  list: (root: string, path = "") => request<FileEntry[]>(`/api/files/list?${q({ root, path })}`),
  read: (root: string, path: string) => request<FileContent>(`/api/files/read?${q({ root, path })}`),
  write: (root: string, path: string, text: string, version: string) =>
    request<FileContent>("/api/files/write", { method: "PUT", body: JSON.stringify({ root, path, text, version }) }),
  undo: (root: string, path: string) => request<FileContent>("/api/files/undo", post({ root, path })),
  propose: (root: string, path: string, instruction: string, thinking: boolean | null) =>
    request<Proposal>("/api/files/propose", post({ root, path, instruction, thinking })),
  apply: (id: string, hunks: number[] | null) => request<FileContent>(`/api/files/proposals/${id}/apply`, post({ hunks })),
  discard: (id: string) => request<{ status: string }>(`/api/files/proposals/${id}`, { method: "DELETE" }),
  run: (root: string, command: string) => request<RunResult>("/api/files/run", post({ root, command })),
};
