// Where routines report. Flagged items say what was flagged, because "an agent read something odd"
// is only useful if you can see the something.
import { Inbox as InboxIcon } from "lucide-react";
import { useAgents } from "../store/agents";
import { Button, Empty } from "../ui/controls";

export default function Inbox() {
  const inbox = useAgents((s) => s.inbox);
  const markRead = useAgents((s) => s.markRead);

  if (inbox.length === 0) {
    return (
      <Empty icon={InboxIcon} title="Nothing yet">
        When a routine runs, what it found lands here.
      </Empty>
    );
  }

  return (
    <div className="-mx-4">
      {inbox.map((item) => (
        <article key={item.id} className="rounded-3xl px-4 py-3.5 transition-colors hover:bg-ink/[0.03]">
          <div className="flex items-center gap-2">
            {!item.read_at && <span className="h-2 w-2 shrink-0 rounded-full bg-accent" />}
            <h3 className={`min-w-0 flex-1 truncate text-[15px] font-medium ${item.read_at ? "text-ink-muted" : "text-ink"}`}>
              {item.title}
            </h3>
            <Button small tone="ghost" onClick={() => void markRead(item.id, !item.read_at)}>
              {item.read_at ? "Mark unread" : "Mark read"}
            </Button>
          </div>
          {item.flags.length > 0 && (
            <p className="mt-1 text-[12.5px] text-danger" title="Something it read was trying to give it instructions.">
              Flagged: {item.flags.join(", ")}
            </p>
          )}
          <p className="mt-1.5 whitespace-pre-wrap text-[14px] leading-relaxed text-ink-muted">{item.body}</p>
        </article>
      ))}
    </div>
  );
}
