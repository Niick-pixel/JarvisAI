// Code mode: a project folder on this PC, and a chat whose tools work inside it - reading files,
// writing them and running commands, each write or command asking you first. The folder and the
// recent ones are remembered; a coder model is used when one is installed.
import { create } from "zustand";
import { useLibrary } from "./library";
import { useSession } from "./session";
import { toast } from "./toast";

const KEY = "jarvis.code";

interface Desktop {
  pywebview?: { api?: { pick_folder?: () => Promise<string | null> } };
}

function load(): { project: string; recent: string[] } {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return { project: "", recent: [], ...(JSON.parse(raw) as { project?: string; recent?: string[] }) };
  } catch {
    // Storage may be unavailable; Code mode simply asks for a folder again.
  }
  return { project: "", recent: [] };
}

export function folderName(path: string): string {
  return path.replace(/[\\/]+$/, "").split(/[\\/]/).pop() || path;
}

interface CodeState {
  project: string;
  recent: string[];
  on: boolean;
  /** Ask for a folder: the desktop's own picker, or a typed path in a browser. */
  choose: () => Promise<string | null>;
  use: (path: string) => void;
  /** A fresh chat in Code mode, on the current project (asking for one if there is none). */
  start: () => Promise<boolean>;
  stop: () => void;
  /** The installed coder model, if there is one - Code mode prefers it to the general model. */
  coder: () => string | null;
}

export const useCode = create<CodeState>((set, get) => ({
  ...load(),
  on: false,

  choose: async () => {
    const picker = (window as unknown as Desktop).pywebview?.api?.pick_folder;
    const chosen = picker ? await picker().catch(() => null) : window.prompt("Project folder (full path):");
    const path = chosen?.trim();
    if (!path) return null;
    get().use(path);
    return path;
  },

  use: (path) => {
    const recent = [path, ...get().recent.filter((p) => p !== path)].slice(0, 6);
    set({ project: path, recent });
    try {
      localStorage.setItem(KEY, JSON.stringify({ project: path, recent }));
    } catch {
      // Remembering is a convenience only.
    }
  },

  start: async () => {
    const project = get().project || (await get().choose());
    if (!project) return false;
    useSession.getState().newChat();
    set({ on: true });
    toast(`Coding in ${folderName(project)}. Writes and commands ask you first.`);
    return true;
  },

  stop: () => set({ on: false }),

  coder: () => {
    const models = useLibrary.getState().models;
    return models.find((m) => /coder|code/i.test(m.model.display_name))?.model.id ?? null;
  },
}));
