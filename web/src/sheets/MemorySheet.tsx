// Memory (BRIEF.md 4.7): everything Jarvis remembers about you, as a timeline - newest first, each
// one linked to the chat that taught it - in plain sentences you can edit or forget in one click.
// Each one is a Markdown file on this PC, with its own history.
import { AnimatePresence, motion } from "framer-motion";
import { Brain, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { MemoryEntry } from "../api/types";
import MemoryItem from "../memory/MemoryItem";
import Sheet from "../shell/Sheet";
import { useMemory } from "../store/memory";
import { Button, Empty, FIELD } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

type Filter = "all" | "auto" | "manual" | "always";
const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "auto", label: "Learned" },
  { key: "manual", label: "Added by you" },
  { key: "always", label: "Always on" },
];

const DAY = 86_400_000;

function bucket(at: number, now: number): string {
  const midnight = new Date(now).setHours(0, 0, 0, 0);
  if (at >= midnight) return "Today";
  if (at >= midnight - DAY) return "Yesterday";
  if (at >= midnight - 6 * DAY) return "This week";
  if (at >= midnight - 29 * DAY) return "This month";
  return new Date(at).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function grouped(entries: MemoryEntry[]): [string, MemoryEntry[]][] {
  const now = Date.now();
  const groups = new Map<string, MemoryEntry[]>();
  for (const entry of [...entries].sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0))) {
    const key = bucket(entry.created_at ?? 0, now);
    groups.set(key, [...(groups.get(key) ?? []), entry]);
  }
  return [...groups];
}

function UndoBar() {
  const forgotten = useMemory((s) => s.forgotten);
  const undo = useMemory((s) => s.undoForget);
  if (!forgotten) return null;
  const one = (forgotten[0]?.title ?? "1 memory").replace(/[.\s]+$/, "");
  const what = forgotten.length === 1 ? `"${one}"` : `${forgotten.length} memories`;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky bottom-0 mt-3 flex items-center gap-3 rounded-2xl bg-ink px-4 py-2.5 text-[13.5px] text-bg shadow-float"
    >
      <span className="min-w-0 flex-1 truncate">Forgot {what}. The file is gone.</span>
      <button type="button" onClick={() => void undo()} className="font-semibold underline-offset-2 hover:underline">
        Undo
      </button>
    </motion.div>
  );
}

export default function MemorySheet() {
  const { entries, refresh, add, loading } = useMemory();
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  useEffect(() => {
    void refresh().catch(() => undefined);
    // Undo is for the moment you forgot something, not for the next time you open the page.
    return () => useMemory.setState({ forgotten: null });
  }, [refresh]);

  const save = () => {
    const text = draft.trim();
    if (!text) return;
    void add(text.slice(0, 56), text, false);
    setDraft("");
  };
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return entries.filter(
      (e) =>
        (filter === "all" || (filter === "always" ? e.always : e.source === filter)) &&
        (!needle || e.content.toLowerCase().includes(needle) || (e.source_title ?? "").toLowerCase().includes(needle)),
    );
  }, [entries, query, filter]);

  return (
    <Sheet title="Memory" subtitle="What Jarvis knows about you, newest first. Kept as files on this PC - edit or forget anything.">
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
      {entries.length > 0 && (
        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          <label className="mr-1 flex min-w-[180px] flex-1 items-center gap-2 rounded-full bg-ink/[0.05] px-3 py-1.5">
            <Search size={14} className="text-ink-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search memories"
              className="w-full bg-transparent text-[13.5px] text-ink outline-none placeholder:text-ink-faint"
            />
          </label>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              className={`rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors ${
                filter === f.key ? "bg-accent/12 text-accent" : "text-ink-muted hover:bg-ink/[0.05]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}
      {!loading && entries.length === 0 && (
        <Empty icon={Brain} title="Nothing yet">
          As you talk, Jarvis notes things worth remembering - your name, your projects, how you like answers - and
          shows you each one as it saves it.
        </Empty>
      )}
      {entries.length > 0 && shown.length === 0 && (
        <p className="px-1 py-6 text-center text-[13.5px] text-ink-faint">Nothing matches.</p>
      )}
      <div className="-mx-4">
        {grouped(shown).map(([day, items]) => (
          <section key={day} className="mt-2">
            <h3 className="px-4 py-1.5 text-[12px] font-semibold uppercase tracking-wide text-ink-faint">{day}</h3>
            <AnimatePresence initial={false}>
              {items.map((entry) => (
                <motion.div
                  key={entry.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.97 }}
                  transition={BOUNCE}
                >
                  <MemoryItem entry={entry} />
                </motion.div>
              ))}
            </AnimatePresence>
          </section>
        ))}
      </div>
      <UndoBar />
    </Sheet>
  );
}
