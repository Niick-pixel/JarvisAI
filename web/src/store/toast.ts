// Short-lived notes in the corner: "Exported to your vault", "Copied". Anything that needs a
// decision is not a toast - approvals and capture have their own cards.
import { create } from "zustand";

export interface Toast {
  id: number;
  text: string;
  tone?: "info" | "error";
}

let next = 1;

interface ToastState {
  toasts: Toast[];
  show: (text: string, tone?: Toast["tone"]) => void;
  dismiss: (id: number) => void;
}

export const useToasts = create<ToastState>((set, get) => ({
  toasts: [],
  show: (text, tone = "info") => {
    const id = next++;
    set((s) => ({ toasts: [...s.toasts.slice(-2), { id, text, tone }] }));
    window.setTimeout(() => get().dismiss(id), tone === "error" ? 6000 : 2600);
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = (text: string, tone?: Toast["tone"]) => useToasts.getState().show(text, tone);
