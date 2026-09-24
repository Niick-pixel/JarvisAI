// The inline `‹ 2/4 ›` switcher. Every edit and every rerun leaves a sibling here, so this is
// how you get back to a version you moved away from - nothing is ever gone.
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect } from "react";
import { useGraph } from "../store/graph";
import { useSession } from "../store/session";
import { IconButton } from "../ui/controls";

export default function SiblingNav({ messageId }: { messageId: string }) {
  const siblings = useGraph((s) => s.siblings[messageId]);
  const loadSiblings = useGraph((s) => s.loadSiblings);
  const switchTo = useGraph((s) => s.switchTo);

  // Every new message may be a new sibling of this one (a retry, an edit), so look again.
  const count = useSession((s) => s.messages.length);
  useEffect(() => {
    void loadSiblings([messageId]).catch(() => undefined);
  }, [messageId, count, loadSiblings]);

  if (!siblings || siblings.ids.length < 2) return null;

  const go = (delta: number) => {
    const next = siblings.ids[(siblings.index + delta + siblings.ids.length) % siblings.ids.length];
    if (next) void switchTo(next);
  };

  return (
    <span className="mr-1 inline-flex items-center text-[13px] tabular-nums text-ink-faint">
      <IconButton icon={ChevronLeft} label="Previous version" size={28} onClick={() => go(-1)} />
      <span className="px-0.5">
        {siblings.index + 1}/{siblings.ids.length}
      </span>
      <IconButton icon={ChevronRight} label="Next version" size={28} onClick={() => go(1)} />
    </span>
  );
}
