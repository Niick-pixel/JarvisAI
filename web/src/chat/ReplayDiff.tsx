// Word-level diff between a rerun and the message it replayed (BRIEF.md 4.5).
// With the same seed the two are identical, which is the point: a difference means a parameter
// changed, not that the model wandered.
import { diffWords } from "diff";
import { useMemo } from "react";
import type { Message } from "../api/types";

export default function ReplayDiff({
  message,
  original,
}: {
  message: Message;
  original: Message | undefined;
}) {
  const parts = useMemo(
    () => (original ? diffWords(original.content, message.content) : []),
    [original, message.content],
  );

  if (!original) {
    return <p className="text-[12px] text-ink-faint">The message this replayed is not loaded.</p>;
  }
  const changed = parts.some((part) => part.added || part.removed);

  return (
    <div className="rounded-2xl border border-ink/[0.08] bg-code p-4">
      <p className="mb-2 text-[12px] font-medium text-ink-faint">
        {changed ? "Differences from the original" : "Identical to the original, byte for byte"}
      </p>
      <p className="whitespace-pre-wrap text-[13px] leading-relaxed">
        {parts.map((part, index) => (
          <span
            key={index}
            className={
              part.added
                ? "bg-success/15 text-success"
                : part.removed
                  ? "bg-danger/10 text-danger line-through"
                  : "text-ink-muted"
            }
          >
            {part.value}
          </span>
        ))}
      </p>
    </div>
  );
}
