// Getting a model onto this machine from inside the app. The server does the work and keeps the
// state; this polls it while something is happening and stops polling when nothing is.
import { create } from "zustand";
import { ApiError, api } from "../api/client";
import type { DownloadProgress, LaunchStatus, ModelRecommendation } from "../api/types";
import { useLibrary } from "./library";

const POLL_MS = 800;
let timer: number | null = null;

interface DownloadsState {
  open: boolean;
  catalog: ModelRecommendation[];
  progress: DownloadProgress | null;
  launch: LaunchStatus | null;
  error: string | null;

  show: () => Promise<void>;
  hide: () => void;
  /** First launch: open by itself when there is nothing to talk to and nothing on disk. */
  checkFirstRun: () => Promise<void>;
  start: (key: string) => Promise<void>;
  cancel: () => Promise<void>;
}

export const useDownloads = create<DownloadsState>((set, get) => ({
  open: false,
  catalog: [],
  progress: null,
  launch: null,
  error: null,

  show: async () => {
    set({ open: true, error: null });
    const [catalog, progress, launch] = await Promise.all([
      api.catalog(),
      api.downloadProgress(),
      api.launchStatus(),
    ]);
    set({ catalog, progress, launch });
    if (isActive(progress)) poll(get, set);
  },

  hide: () => set({ open: false }),

  checkFirstRun: async () => {
    const [providers, launch, progress] = await Promise.all([
      api.providers(),
      api.launchStatus(),
      api.downloadProgress(),
    ]);
    set({ launch, progress });
    const nothingOnline = !providers.some((p) => p.online);
    const waitingForAModel = launch.autostart && !launch.started && !launch.model_path;
    if ((nothingOnline && waitingForAModel) || isActive(progress)) await get().show();
  },

  start: async (key: string) => {
    set({ error: null });
    try {
      set({ progress: await api.startDownload(key) });
      poll(get, set);
    } catch (error) {
      set({ error: error instanceof ApiError ? error.body.message : String(error) });
    }
  },

  cancel: async () => {
    set({ progress: await api.cancelDownload() });
  },
}));

function isActive(progress: DownloadProgress | null): boolean {
  return !!progress && ["resolving", "downloading", "verifying"].includes(progress.state);
}

type Get = () => DownloadsState;
type Set = (partial: Partial<DownloadsState>) => void;

function poll(get: Get, set: Set): void {
  if (timer !== null) return;
  timer = window.setInterval(() => {
    void (async () => {
      const progress = await api.downloadProgress().catch(() => null);
      if (!progress) return;
      set({ progress });
      if (isActive(progress)) return;
      if (timer !== null) window.clearInterval(timer);
      timer = null;
      if (progress.state !== "done") return;
      // The server pins the new model and starts llama-server on it; follow it until it serves.
      for (let i = 0; i < 90; i += 1) {
        const launch = await api.launchStatus().catch(() => null);
        if (launch) set({ launch });
        if (!launch || launch.started || (launch.detail && !launch.detail.startsWith("starting")))
          break;
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      set({ catalog: await api.catalog().catch(() => get().catalog) });
      void useLibrary.getState().refreshModels().catch(() => undefined);
    })();
  }, POLL_MS);
}
