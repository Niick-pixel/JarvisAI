// Images waiting to go with the next message: photos you add, paste or drop, and screenshots.
// Photos are scaled down in the browser first - a model sees a 12-megapixel photo at a fraction
// of that anyway, and a smaller upload is a faster answer.
import { create } from "zustand";
import { ApiError, request } from "../api/client";
import type { Attachment } from "../api/types";
import { toast } from "./toast";

const LONGEST = 1600;

interface Desktop {
  pywebview?: { api?: { capture_screen?: () => Promise<Attachment | null> } };
}

async function shrink(file: File): Promise<Blob> {
  if (file.type === "image/gif") return file;
  const bitmap = await createImageBitmap(file).catch(() => null);
  if (!bitmap || Math.max(bitmap.width, bitmap.height) <= LONGEST) return file;
  const scale = LONGEST / Math.max(bitmap.width, bitmap.height);
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, "image/jpeg", 0.9));
  return blob ?? file;
}

const upload = (body: Blob) =>
  request<Attachment>("/api/attachments", { method: "POST", body, headers: { "Content-Type": body.type } });

interface AttachmentsState {
  pending: Attachment[];
  busy: boolean;
  addFiles: (files: File[]) => Promise<void>;
  captureScreen: () => Promise<void>;
  add: (attachment: Attachment) => void;
  remove: (id: string) => void;
  take: () => string[];
}

export const useAttachments = create<AttachmentsState>((set, get) => ({
  pending: [],
  busy: false,

  addFiles: async (files) => {
    set({ busy: true });
    try {
      for (const file of files.filter((f) => f.type.startsWith("image/"))) {
        try {
          get().add(await upload(await shrink(file)));
        } catch (error) {
          toast(error instanceof ApiError ? error.body.message : `Couldn't add ${file.name}`, "error");
        }
      }
    } finally {
      set({ busy: false });
    }
  },

  captureScreen: async () => {
    set({ busy: true });
    try {
      // In the app the window steps aside for the capture; in a browser the server takes it.
      const native = (window as unknown as Desktop).pywebview?.api?.capture_screen;
      const shot = native ? await native() : await request<Attachment>("/api/screen/capture", { method: "POST" });
      if (shot) get().add(shot);
      else toast("Couldn't capture the screen", "error");
    } catch (error) {
      toast(error instanceof ApiError ? error.body.message : "Couldn't capture the screen", "error");
    } finally {
      set({ busy: false });
    }
  },

  add: (attachment) => set((s) => ({ pending: [...s.pending, attachment] })),
  remove: (id) => set((s) => ({ pending: s.pending.filter((a) => a.id !== id) })),

  /** The ids for the message being sent, clearing the tray. */
  take: () => {
    const ids = get().pending.map((a) => a.id);
    set({ pending: [] });
    return ids;
  },
}));
