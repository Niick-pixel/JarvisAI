// Sharing your screen: while it is on, every message you send - typed or spoken - carries what is
// on your screen at that moment, and a live thumbnail above the composer shows what Jarvis sees.
// In the app, Jarvis's own window is left out of the capture, so it sees what is behind it.
import { create } from "zustand";
import { request } from "../api/client";
import type { Attachment } from "../api/types";
import { useAttachments } from "./attachments";
import { toast } from "./toast";

interface Desktop {
  pywebview?: {
    api?: { exclude_from_capture?: (on: boolean) => Promise<boolean> };
  };
}

const desktop = () => (window as unknown as Desktop).pywebview?.api;

interface ShareState {
  on: boolean;
  start: () => Promise<void>;
  stop: () => void;
  /** A fresh frame onto the outgoing message. Called by send, just before it goes. */
  attachNow: () => Promise<void>;
}

export const useScreenShare = create<ShareState>((set, get) => ({
  on: false,
  start: async () => {
    // One frame first: if the screen cannot be captured, say so now rather than at send.
    const probe = await fetch("/api/screen/frame?size=120").catch(() => null);
    if (!probe?.ok) {
      const body = (await probe?.json().catch(() => null)) as {
        message?: string;
      } | null;
      toast(body?.message ?? "Couldn't see the screen", "error");
      return;
    }
    await desktop()
      ?.exclude_from_capture?.(true)
      .catch(() => false);
    set({ on: true });
    toast("Sharing your screen. Everything you send includes it.");
  },
  stop: () => {
    void desktop()
      ?.exclude_from_capture?.(false)
      .catch(() => false);
    set({ on: false });
  },
  attachNow: async () => {
    if (!get().on) return;
    try {
      const shot = await request<Attachment>("/api/screen/capture", {
        method: "POST",
      });
      useAttachments.getState().add(shot);
    } catch {
      toast("Couldn't capture the screen for this message", "error");
    }
  },
}));
