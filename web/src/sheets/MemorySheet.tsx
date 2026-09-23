// Memory (BRIEF.md 4.7): everything Jarvis remembers about you, in plain sentences you can edit
// or delete. Each one is a Markdown file on this PC, with its own history.
import { AnimatePresence, motion } from "framer-motion";
import { Brain, History, Pencil, Pin, PinOff, Plus, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { MemoryCommit, MemoryEntry } from "../api/types";
import Sheet from "../shell/Sheet";
import { useMemory } from "../store/memory";
import { Button, Empty, FIELD, IconButton } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

function origin(entry: MemoryEntry): string {
  const from = entry.source === "auto" ? "Learned in a chat" : "Added by you";
  if (!entry.retrieved_count) return `${from} · not used yet`;
  const n = entry.retrieved_count;
  return `${from} · used ${n === 1 ? "once" : `${n} times`}`;
}

function Item({ entry }: { entry: MemoryEntry }) {
  const { edit, forget } = useMemory();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry.content);
  const [history, setHistory] = useState<MemoryCommit[] | null>(null);

  return (
    <div className="group rounded-3xl px-4 py-3.5 transition-colors hover:bg-ink/[0.03]">
      {editing ? (
        <div className="space-y-2">
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={3} autoFocus className={`${FIELD} resize-y`} />
          <div className="flex gap-2">
            <Button small tone="primary" onClick={() => void edit(entry.id, { content: draft }).then(() => setEditing(false))}>
              Save
            </Button>
            <Button small tone="ghost" onClick={() => setEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-[15px] leading-snug text-ink">{entry.content}</p>
            <p className="mt-1 text-[12.5px] text-ink-faint">
              {entry.always && <span className="mr-1.5 font-medium text-accent">Always on ·</span>}
              {origin(entry)}
            </p>
          </div>
          <div className="flex opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
            <IconButton
              icon={entry.always ? PinOff : Pin}
              label={entry.always ? "Only when relevant" : "Always keep in mind"}
              size={32}
              onClick={() => void edit(entry.id, { always: !entry.always })}
            />
            <IconButton icon={Pencil} label="Edit" size={32} onClick={() => setEditing(true)} />
            <IconButton icon={History} label="History" size={32} onClick={() => void api.memoryHistory(entry.id).then(setHistory)} />
            <IconButton icon={Trash2} label="Forget" size={32} onClick={() => void forget(entry.id)} />
          </div>
        </div>
      )}
      {history && (
        <ul className="mt-2 space-y-0.5 rounded-2xl bg-code p-3 font-mono text-[11.5px] text-ink-faint">
          {history.length === 0 && <li>No history for this one yet.</li>}
          {history.map((c) => (
            <li key={c.sha} className="truncate">
              {c.sha.slice(0, 7)} {c.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MemorySheet() {
  const { entries, refresh, add, loading } = useMemory();
  const [draft, setDraft] = useState("");

  useEffect(() => {
    void refresh().catch(() => undefined);
  }, [refresh]);

  const save = () => {
    const text = draft.trim();
    if (!text) return;
    void add(text.slice(0, 56), text, false);
    setDraft("");
  };
  const sorted = [...entries].sort((a, b) => Number(b.always) - Number(a.always));

  return (
    <Sheet title="Memory" subtitle="What Jarvis knows about you. Kept as files on this PC - edit or delete anything.">
      <div className="mb-3 flex gap-2">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && save()}
          placeholder="Tell Jarvis something to remember"
          className={FIELD}
        />
        <Button tone="primary" icon={Plus} onClick={save} disabled={!draft.trim()}>
          Add
        </Button>
      </div>
      {!loading && entries.length === 0 && (
        <Empty icon={Brain} title="Nothing yet">
          As you talk, Jarvis notes things worth remembering - your name, your projects, how you like answers - and
          shows you each one as it saves it.
        </Empty>
      )}
      <div className="-mx-4">
        <AnimatePresence initial={false}>
          {sorted.map((entry) => (
            <motion.div key={entry.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.97 }} transition={BOUNCE}>
              <Item entry={entry} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Sheet>
  );
}
