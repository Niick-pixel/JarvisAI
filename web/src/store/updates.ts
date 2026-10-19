// What the updater is doing. Polled slowly at rest and quickly while a download runs, so the
// sidebar can say "Restart to update" the moment the new version is verified.
import { create } from "zustand";
import type { UpdateStatus } from "../api/types";
import { updatesApi } from "../api/updates";
import { toast } from "./toast";

const BUSY = ["checking", "downloading", "installing"];

interface UpdatesState {
  status: UpdateStatus | null;
  refresh: () => Promise<void>;
  check: () => Promise<void>;
  download: () => Promise<void>;
  install: () => Promise<void>;
  /** One click: fetch the new version if needed, then restart into it as soon as it verifies. */
  updateNow: () => Promise<void>;
  installWhenReady: boolean;
  setAuto: (auto: boolean) => Promise<void>;
}

export const useUpdates = create<UpdatesState>((set, get) => {
  const apply = (status: UpdateStatus) => set({ status });
  const quietly = (call: () => Promise<UpdateStatus>) => async () => {
    try {
      apply(await call());
    } catch {
      // An old server without the updater, or one that is restarting: nothing to show.
    }
  };
  return {
    status: null,
    refresh: quietly(updatesApi.status),
    check: async () => {
      const status = await updatesApi.check().catch(() => null);
      if (!status) return toast("Couldn't check for updates.", "error");
      apply(status);
      if (status.state === "up_to_date") toast(`Jarvis ${status.current} is the latest version.`);
    },
    download: quietly(updatesApi.download),
    install: quietly(updatesApi.install),
    installWhenReady: false,
    updateNow: async () => {
      if (get().status?.state === "ready") return get().install();
      set({ installWhenReady: true });
      await get().download();
    },
    setAuto: async (auto) => quietly(() => updatesApi.setAuto(auto))(),
  };
});

/** Starts polling; returns the stop function. Called once, from the sidebar. */
export function watchUpdates(): () => void {
  let timer = 0;
  const tick = async () => {
    const updates = useUpdates.getState();
    await updates.refresh();
    const state = useUpdates.getState().status?.state ?? "";
    if (updates.installWhenReady && state === "ready") {
      useUpdates.setState({ installWhenReady: false });
      await updates.install();
    } else if (updates.installWhenReady && state === "failed") {
      useUpdates.setState({ installWhenReady: false });
    }
    timer = window.setTimeout(() => void tick(), BUSY.includes(state) ? 1000 : 60_000);
  };
  void tick();
  return () => window.clearTimeout(timer);
}
