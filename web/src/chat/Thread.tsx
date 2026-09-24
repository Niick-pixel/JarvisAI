// The conversation, one centred column. It follows the answer as it streams - unless you have
// scrolled up to read something, in which case it leaves you alone.
import { useEffect, useRef } from "react";
import { useSession } from "../store/session";
import ErrorCard from "./ErrorCard";
import { AssistantTurn, UserTurn } from "./Turn";

export default function Thread() {
  const messages = useSession((s) => s.messages);
  const activePath = useSession((s) => s.activePath);
  const streamingId = useSession((s) => s.streamingId);
  const scroller = useRef<HTMLDivElement>(null);
  const column = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);

  const onPath = new Set(activePath);
  const visible = messages.filter(
    (m) => (onPath.has(m.id) || m.id === streamingId) && (m.role === "user" || m.role === "assistant"),
  );

  useEffect(() => {
    // Follow the column as it grows - tokens, the action row arriving, a thinking panel opening -
    // but only while you are already at the bottom.
    const el = scroller.current;
    const body = column.current;
    if (!el || !body) return;
    const follow = () => {
      if (pinned.current) el.scrollTop = el.scrollHeight;
    };
    const observer = new ResizeObserver(follow);
    observer.observe(body);
    follow();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    // Sending is always a reason to jump to the bottom.
    pinned.current = true;
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [visible.length]);

  return (
    <div
      ref={scroller}
      onScroll={(e) => {
        const el = e.currentTarget;
        pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      }}
      className="scroll-quiet min-h-0 flex-1 overflow-y-auto"
    >
      <div ref={column} className="mx-auto flex w-full max-w-[760px] flex-col gap-8 px-6 pb-10 pt-6">
        {visible.map((message) =>
          message.role === "user" ? (
            <UserTurn key={message.id} message={message} />
          ) : (
            <AssistantTurn key={message.id} message={message} streaming={message.id === streamingId} />
          ),
        )}
        <ErrorCard />
      </div>
    </div>
  );
}
