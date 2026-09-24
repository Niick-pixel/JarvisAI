// How full the model's memory of this chat is. Invisible until it matters: the ring appears when
// the conversation passes 70% of what the model can hold (or always, with developer tools on),
// and opens onto exactly what is being sent and what had to be left out.
import { useEffect } from "react";
import { useContextInspector } from "../store/context";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";
import { Tip } from "../ui/controls";
import Menu from "../ui/Menu";
import Inspector from "./Inspector";

const SHOW_AT = 0.7;

export default function ContextRing() {
  const live = useSession((s) => s.assembly);
  const conversationId = useSession((s) => s.conversation?.id);
  const count = useSession((s) => s.messages.length);
  const preview = useContextInspector((s) => s.preview);
  const refresh = useContextInspector((s) => s.refresh);
  const devTools = useUi((s) => s.devTools);

  useEffect(() => {
    if (conversationId) void refresh().catch(() => undefined);
  }, [conversationId, count, refresh]);

  const assembly = live ?? (conversationId ? preview : null);
  if (!assembly) return null;
  const budget = Math.max(1, assembly.ctx_len - assembly.max_gen_tokens);
  const used = Math.min(1, assembly.total_tokens / budget);
  const evicted = assembly.evictions.length > 0;
  if (!devTools && used < SHOW_AT && !evicted) return null;

  const r = 8;
  const circumference = 2 * Math.PI * r;
  const tone = used > 0.92 || evicted ? "text-danger" : "text-accent";

  return (
    <Menu
      place="top-end"
      width={380}
      items={[]}
      header={<Inspector assembly={assembly} live={!!live} />}
      trigger={(_, toggle) => (
        <button
          type="button"
          onClick={toggle}
          aria-label="What Jarvis is reading"
          className="group/tip relative flex h-10 w-10 items-center justify-center rounded-full transition-colors hover:bg-ink/[0.06]"
        >
          <svg width="22" height="22" viewBox="0 0 22 22" className="-rotate-90">
            <circle cx="11" cy="11" r={r} fill="none" strokeWidth="2.5" className="stroke-ink/10" />
            <circle
              cx="11"
              cy="11"
              r={r}
              fill="none"
              strokeWidth="2.5"
              strokeLinecap="round"
              stroke="currentColor"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - used)}
              className={`${tone} transition-[stroke-dashoffset] duration-500`}
            />
          </svg>
          <Tip side="top">{Math.round(used * 100)}% of the model's memory</Tip>
        </button>
      )}
    />
  );
}
