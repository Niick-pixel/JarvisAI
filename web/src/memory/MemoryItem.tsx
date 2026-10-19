// One memory on the timeline: the sentence, where it was learned (a link back to that chat), the
// chats it has been used in since, and the hands-on controls - pin, edit, history, forget.
import { History, MessageSquare, Pencil, Pin, PinOff, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "../api/client";
import { memoryApi } from "../api/memory";
import type { MemoryCommit, MemoryEntry, MemoryUse } from "../api/types";
import { useMemory } from "../store/memory";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";
import { Button, FIELD, IconButton } from "../ui/controls";

function openChat(conversationId: string) {
  void useSession.getState().openConversation(conversationId);
  useUi.getState().closeSheet();
}

function ChatLink({ id, title }: { id: string; title: string }) {
  return (
    <button type="button" onClick={() => openChat(id)} className="inline-flex max-w-full items-center gap-1 font-medium text-accent hover:underline">
      <MessageSquare size={12} strokeWidth={2} className="shrink-0" />
      <span className="truncate">{title || "Untitled chat"}</span>
    </button>
  );
}

function Origin({ entry }: { entry: MemoryEntry }) {
  if (entry.source === "manual") return <span>Added by you</span>;
  if (!entry.source_conversation_id) return <span>Learned in a chat</span>;
  if (!entry.source_title) return <span>Learned in a chat you have since deleted</span>;
  return (
    <span className="inline-flex min-w-0 items-center gap-1">
      Learned in <ChatLink id={entry.source_conversation_id} title={entry.source_title} />
    </span>
  );
}

function Uses({ entry }: { entry: MemoryEntry }) {
  const [uses, setUses] = useState<MemoryUse[] | null>(null);
  const forgetChat = useMemory((s) => s.forgetChat);
  const n = entry.retrieved_count ?? 0;
  return (
    <>
      {n > 0 ? (
        <button type="button" onClick={() => void memoryApi.uses(entry.id).then(setUses)} className="hover:text-ink">
          used {n === 1 ? "once" : `${n} times`}
        </button>
      ) : (
        <span>not used yet</span>
      )}
      {uses && (
        <div className="mt-2 w-full space-y-1 rounded-2xl bg-ink/[0.03] p-3">
          <p className="text-[12px] font-medium text-ink-muted">Brought into</p>
          {uses.map((u) => (
            <div key={u.conversation_id} className="flex items-center gap-2 text-[12.5px]">
              <ChatLink id={u.conversation_id} title={u.title} />
              <span className="ml-auto shrink-0">{u.times === 1 ? "once" : `${u.times}×`}</span>
            </div>
          ))}
          {entry.source_conversation_id && entry.source_title && (
            <button
              type="button"
              onClick={() => void forgetChat(entry.source_conversation_id ?? "")}
              className="pt-1 text-[12px] font-medium text-danger hover:underline"
            >
              Forget everything learned in "{entry.source_title}"
            </button>
          )}
        </div>
      )}
    </>
  );
}

export default function MemoryItem({ entry }: { entry: MemoryEntry }) {
  const { edit, forget } = useMemory();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry.content);
  const [history, setHistory] = useState<MemoryCommit[] | null>(null);

  if (editing) {
    return (
      <div className="space-y-2 rounded-3xl px-4 py-3.5">
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
    );
  }
  return (
    <div className="group rounded-3xl px-4 py-3 transition-colors hover:bg-ink/[0.03]">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[15px] leading-snug text-ink">{entry.content}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-1.5 text-[12.5px] text-ink-faint">
            {entry.always && <span className="font-medium text-accent">Always on ·</span>}
            <Origin entry={entry} />
            <span>·</span>
            <Uses entry={entry} />
          </div>
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
