// The Files workspace: open folders, the expanded tree, the open file and its unsaved text, and the
// proposal Jarvis is waiting on you to review.
import { create } from "zustand";
import { filesApi } from "../api/files";
import type { FileContent, FileEntry, FileRoot, Proposal, RunResult } from "../api/types";
import { toast } from "./toast";
import { thinkingParams, useUi } from "./ui";

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

interface FilesState {
  roots: FileRoot[];
  root: string | null;
  children: Record<string, FileEntry[]>;
  open: Record<string, boolean>;
  file: FileContent | null;
  draft: string;
  proposal: Proposal | null;
  rejected: Record<number, boolean>;
  asking: boolean;
  run: RunResult | null;
  running: boolean;
  refresh: () => Promise<void>;
  addRoot: (path: string) => Promise<void>;
  closeRoot: (id: string) => Promise<void>;
  pickRoot: (id: string) => Promise<void>;
  toggle: (entry: FileEntry) => Promise<void>;
  openFile: (path: string) => Promise<void>;
  setDraft: (text: string) => void;
  save: () => Promise<void>;
  undo: () => Promise<void>;
  ask: (instruction: string) => Promise<void>;
  flip: (hunk: number) => void;
  apply: () => Promise<void>;
  discard: () => Promise<void>;
  runCommand: (command: string) => Promise<void>;
}

export const useFiles = create<FilesState>((set, get) => {
  const guard = async (work: () => Promise<void>) => {
    try {
      await work();
    } catch (error) {
      toast(message(error), "error");
    }
  };
  const loaded = (file: FileContent) => set({ file, draft: file.text, proposal: null, rejected: {} });
  return {
    roots: [],
    root: null,
    children: {},
    open: {},
    file: null,
    draft: "",
    proposal: null,
    rejected: {},
    asking: false,
    run: null,
    running: false,
    refresh: () =>
      guard(async () => {
        const roots = await filesApi.roots();
        set({ roots });
        const root = get().root ?? roots[0]?.id ?? null;
        if (root) await get().pickRoot(root);
      }),
    addRoot: (path) =>
      guard(async () => {
        const root = await filesApi.addRoot(path);
        set({ roots: await filesApi.roots() });
        await get().pickRoot(root.id);
      }),
    closeRoot: (id) =>
      guard(async () => {
        const roots = await filesApi.removeRoot(id);
        set({ roots, root: null, children: {}, file: null, proposal: null });
        if (roots[0]) await get().pickRoot(roots[0].id);
      }),
    pickRoot: (id) =>
      guard(async () => {
        set({ root: id, children: { "": await filesApi.list(id) }, open: {}, file: null, proposal: null, run: null });
      }),
    toggle: (entry) =>
      guard(async () => {
        const root = get().root;
        if (!root) return;
        if (!entry.dir) return get().openFile(entry.path);
        const opening = !get().open[entry.path];
        set((s) => ({ open: { ...s.open, [entry.path]: opening } }));
        if (opening && !get().children[entry.path]) {
          const listed = await filesApi.list(root, entry.path);
          set((s) => ({ children: { ...s.children, [entry.path]: listed } }));
        }
      }),
    openFile: (path) =>
      guard(async () => {
        const root = get().root;
        if (root) loaded(await filesApi.read(root, path));
      }),
    setDraft: (draft) => set({ draft }),
    save: () =>
      guard(async () => {
        const { file, draft } = get();
        if (!file) return;
        loaded(await filesApi.write(file.root, file.path, draft, file.version));
        toast(`Saved ${file.path}.`);
      }),
    undo: () =>
      guard(async () => {
        const file = get().file;
        if (!file) return;
        loaded(await filesApi.undo(file.root, file.path));
        toast("Restored the previous version.");
      }),
    ask: async (instruction) => {
      const file = get().file;
      if (!file || !instruction.trim()) return;
      set({ asking: true });
      await guard(async () => {
        const { thinking } = thinkingParams(useUi.getState().think);
        set({ proposal: await filesApi.propose(file.root, file.path, instruction, thinking), rejected: {} });
      });
      set({ asking: false });
    },
    flip: (hunk) => set((s) => ({ rejected: { ...s.rejected, [hunk]: !s.rejected[hunk] } })),
    apply: () =>
      guard(async () => {
        const { proposal, rejected } = get();
        if (!proposal) return;
        const keep = proposal.hunks.filter((h) => !rejected[h.index]).map((h) => h.index);
        loaded(await filesApi.apply(proposal.id, keep));
        toast(`Applied ${keep.length} of ${proposal.hunks.length} changes. Undo is one click away.`);
      }),
    discard: () =>
      guard(async () => {
        const proposal = get().proposal;
        set({ proposal: null, rejected: {} });
        if (proposal) await filesApi.discard(proposal.id);
      }),
    runCommand: async (command) => {
      const root = get().root;
      if (!root || !command.trim()) return;
      set({ running: true });
      await guard(async () => set({ run: await filesApi.run(root, command) }));
      set({ running: false });
    },
  };
});
