// Jarvis's side: say what to change, then read every change as a diff and keep the ones you want.
// Nothing touches the file until Apply.
import { ArrowUp, Check, X } from "lucide-react";
import { useState } from "react";
import type { Hunk } from "../api/types";
import { useFiles } from "../store/files";
import { Button } from "../ui/controls";

function HunkView({ hunk }: { hunk: Hunk }) {
  const rejected = useFiles((s) => s.rejected[hunk.index]) ?? false;
  const flip = useFiles((s) => s.flip);
  const line = (text: string, tone: string, sign: string, key: string) => (
    <div key={key} className={`whitespace-pre-wrap break-words px-3 ${tone}`}>
      <span className="mr-2 select-none opacity-50">{sign}</span>
      {text || " "}
    </div>
  );
  return (
    <div className={`overflow-hidden rounded-2xl border border-ink/[0.08] transition-opacity ${rejected ? "opacity-45" : ""}`}>
      <div className="flex items-center justify-between bg-ink/[0.03] px-3 py-1.5 text-[12px] text-ink-muted">
        <span>Line {hunk.old_start}</span>
        <button
          type="button"
          onClick={() => flip(hunk.index)}
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium ${rejected ? "text-ink-muted hover:text-ink" : "text-accent"}`}
        >
          {rejected ? <X size={13} /> : <Check size={13} />}
          {rejected ? "Skipped" : "Keep"}
        </button>
      </div>
      <div className="py-1 font-mono text-[12px] leading-relaxed">
        {hunk.before.map((t, i) => line(t, "text-ink-faint", " ", `b${i}`))}
        {hunk.old.map((t, i) => line(t, "bg-danger/10 text-ink", "−", `o${i}`))}
        {hunk.new.map((t, i) => line(t, "bg-success/10 text-ink", "+", `n${i}`))}
        {hunk.after.map((t, i) => line(t, "text-ink-faint", " ", `a${i}`))}
      </div>
    </div>
  );
}

export default function Changes() {
  const { file, proposal, rejected, asking, ask, apply, discard } = useFiles();
  const [instruction, setInstruction] = useState("");
  if (!file) return <p className="px-1 pt-2 text-[13px] text-ink-faint">Open a file to ask Jarvis to change it.</p>;
  const kept = proposal ? proposal.hunks.filter((h) => !rejected[h.index]).length : 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-end gap-2 rounded-3xl border border-ink/[0.08] bg-surface p-1.5 pl-4 shadow-card">
        <textarea
          rows={2}
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void ask(instruction);
            }
          }}
          placeholder={`What should change in ${file.path.split("/").pop()}?`}
          className="min-w-0 flex-1 resize-none bg-transparent py-2 text-[14px] text-ink outline-none placeholder:text-ink-faint"
        />
        <button
          type="button"
          aria-label="Ask Jarvis"
          disabled={asking || !instruction.trim()}
          onClick={() => void ask(instruction)}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-ink text-bg disabled:opacity-25"
        >
          <ArrowUp size={18} strokeWidth={2} />
        </button>
      </div>
      {asking && <p className="shimmer mt-3 px-1 text-[13.5px] font-medium">Reading the file and writing changes</p>}

      {proposal && (
        <div className="scroll-quiet mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          <p className="px-1 text-[13.5px] text-ink">{proposal.summary}</p>
          {proposal.hunks.length === 0 && (
            <p className="px-1 text-[13px] text-ink-muted">The edits leave the file exactly as it is.</p>
          )}
          {proposal.hunks.map((hunk) => (
            <HunkView key={hunk.index} hunk={hunk} />
          ))}
          {proposal.failed.length > 0 && (
            <div className="rounded-2xl bg-danger/[0.07] p-3 text-[12.5px] text-ink">
              {proposal.failed.length === 1
                ? "One edit pointed at text that is not in the file, so it was left out:"
                : `${proposal.failed.length} edits pointed at text that is not in the file, so they were left out:`}
              {proposal.failed.map((f) => (
                <pre key={f} className="mt-1 whitespace-pre-wrap font-mono text-[11.5px] text-ink-muted">
                  {f}
                </pre>
              ))}
            </div>
          )}
        </div>
      )}
      {proposal && (
        <div className="mt-3 flex items-center gap-2">
          <Button small tone="primary" disabled={kept === 0} onClick={() => void apply()}>
            Apply {kept} of {proposal.hunks.length}
          </Button>
          <Button small tone="ghost" onClick={() => void discard()}>
            Discard
          </Button>
          <span className="ml-auto text-[12px] text-ink-faint">{(proposal.elapsed_ms / 1000).toFixed(1)}s</span>
        </div>
      )}
    </div>
  );
}
