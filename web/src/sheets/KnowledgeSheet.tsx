// Knowledge (BRIEF.md 4.8): folders of your own documents that Jarvis can search and cite. Every
// answer that uses one names the file and the exact place in it.
import { motion } from "framer-motion";
import { FolderOpen, FolderPlus, Library, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { IndexProgress, RetrievalStatus, Source } from "../api/types";
import Sheet from "../shell/Sheet";
import { Button, Empty, FIELD, IconButton, Row, Switch } from "../ui/controls";
import { GLIDE } from "../ui/motion";

interface Desktop {
  pywebview?: { api?: { pick_folder?: () => Promise<string | null> } };
}

const picker = () => (window as unknown as Desktop).pywebview?.api?.pick_folder;

function basename(path: string): string {
  return path.replace(/[\\/]+$/, "").split(/[\\/]/).pop() || path;
}

function SourceRow({ source, live, onChange }: { source: Source; live?: IndexProgress; onChange: () => void }) {
  const working = live && live.state !== "done" && live.state !== "idle";
  const pct = live?.files_total ? Math.round((live.files_done / live.files_total) * 100) : 0;
  return (
    <div className="group flex items-start gap-3 rounded-3xl px-4 py-3.5 transition-colors hover:bg-ink/[0.03]">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-glow-c/25 text-ink-muted">
        <FolderOpen size={19} strokeWidth={1.75} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-medium text-ink">{basename(source.path)}</p>
        <p className="truncate text-[12.5px] text-ink-faint" title={source.path}>
          {source.path}
        </p>
        {working ? (
          <>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-ink/[0.07]">
              <motion.div className="h-full rounded-full bg-accent" animate={{ width: `${pct}%` }} transition={GLIDE} />
            </div>
            <p className="mt-1 text-[12px] text-ink-faint">Reading {live.files_done} of {live.files_total} files…</p>
          </>
        ) : (
          <p className="mt-1 text-[12.5px] text-ink-faint">
            {source.file_count.toLocaleString()} files · {source.chunk_count.toLocaleString()} passages
          </p>
        )}
      </div>
      <div className="flex opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <IconButton icon={RefreshCw} label="Read again" size={32} onClick={() => void api.indexSource(source.id).catch(() => undefined)} />
        <IconButton icon={Trash2} label="Remove" size={32} onClick={() => void api.removeSource(source.id).then(onChange)} />
      </div>
    </div>
  );
}

export default function KnowledgeSheet() {
  const [sources, setSources] = useState<Source[]>([]);
  const [progress, setProgress] = useState<Record<string, IndexProgress>>({});
  const [status, setStatus] = useState<RetrievalStatus | null>(null);
  const [typing, setTyping] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [list, stat] = await Promise.all([api.sources(), api.retrievalStatus()]);
    setSources(list);
    setStatus(stat);
  }, []);

  useEffect(() => {
    void load().catch(() => undefined);
    const timer = window.setInterval(() => {
      void api
        .indexProgress()
        .then((rows) => setProgress(Object.fromEntries(rows.map((r) => [r.source_id, r]))))
        .catch(() => undefined);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [load]);

  const add = async (path: string) => {
    setError("");
    try {
      await api.addSource(path);
      setTyping(null);
      await load();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.body.message : String(cause));
    }
  };

  const choose = async () => {
    const pick = picker();
    if (!pick) return setTyping("");
    const path = await pick();
    if (path) await add(path);
  };

  return (
    <Sheet
      title="Knowledge"
      subtitle="Folders of your documents that Jarvis can search, with the source named in every answer."
      actions={
        <Button tone="primary" icon={FolderPlus} onClick={() => void choose()}>
          Add folder
        </Button>
      }
    >
      {typing !== null && (
        <div className="mb-3 flex gap-2">
          <input
            autoFocus
            value={typing}
            onChange={(e) => setTyping(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && typing.trim() && void add(typing.trim())}
            placeholder="C:\Users\you\Documents\Notes"
            className={FIELD}
          />
          <Button tone="ghost" onClick={() => setTyping(null)}>
            Cancel
          </Button>
        </div>
      )}
      {error && <p className="mb-3 rounded-2xl bg-danger/[0.07] px-4 py-2.5 text-[13px] text-ink">{error}</p>}
      {sources.length === 0 ? (
        <Empty icon={Library} title="No folders yet">
          Add a folder of notes, PDFs or code. Jarvis reads it on this PC, keeps it up to date as files change, and
          cites the exact passage whenever it uses one.
        </Empty>
      ) : (
        <div className="-mx-4">
          {sources.map((source) => (
            <SourceRow key={source.id} source={source} live={progress[source.id]} onChange={() => void load()} />
          ))}
        </div>
      )}
      <div className="mt-4 divide-y divide-ink/[0.06] border-t border-ink/[0.06]">
        <Row title="Pause reading" detail="It already waits while Jarvis is answering; this stops it entirely.">
          <Switch
            label="Pause reading"
            checked={paused}
            onChange={(next) => {
              setPaused(next);
              void api.pauseIndexing(next).catch(() => undefined);
            }}
          />
        </Row>
        {status && (
          <Row
            title="How it searches"
            detail={`${status.vector ? "By meaning and by keyword" : "By keyword only"}${status.rerank ? ", then re-ranked for relevance" : ""}. ${status.vector ? "" : status.detail}`}
          />
        )}
      </div>
    </Sheet>
  );
}
