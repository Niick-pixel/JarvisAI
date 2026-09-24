// The Council (BRIEF.md 4.6): one question, several models side by side, and a judge that reads
// them without knowing which model wrote which.
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Scale } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ScoreboardRow } from "../api/types";
import Markdown from "../chat/Markdown";
import { split } from "../chat/reasoning";
import AgreementMatrix from "../council/AgreementMatrix";
import Sheet from "../shell/Sheet";
import { useCouncil } from "../store/council";
import { useLibrary } from "../store/library";
import { Empty } from "../ui/controls";
import { BOUNCE } from "../ui/motion";

export default function CouncilSheet() {
  const [question, setQuestion] = useState("");
  const [scores, setScores] = useState<ScoreboardRow[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const models = useLibrary((s) => s.models);
  const council = useCouncil();
  const nameOf = (id: string) => models.find((m) => m.model.id === id)?.model.display_name ?? id.split(":").pop();

  useEffect(() => {
    void useLibrary.getState().refreshModels().catch(() => undefined);
    void api.scoreboard().then(setScores).catch(() => undefined);
  }, []);

  const start = async () => {
    await council.run(question, picked, "general");
    void api.scoreboard().then(setScores).catch(() => undefined);
  };
  const labels = council.members.map((m) => m.label);

  return (
    <Sheet title="Council" subtitle="Ask several models at once. A judge compares the answers without knowing who wrote them." width={1080}>
      <div className="flex items-center gap-2 rounded-full border border-ink/[0.08] bg-surface p-1.5 pl-5 shadow-card">
        <input
          value={question}
          autoFocus
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void start()}
          placeholder="Ask every model the same thing"
          className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-ink-faint"
        />
        <button
          type="button"
          onClick={() => void start()}
          disabled={council.running || !question.trim()}
          aria-label="Ask the council"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-bg disabled:opacity-25"
        >
          <ArrowUp size={20} strokeWidth={2} />
        </button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {models.map((option) => {
          const on = picked.includes(option.model.id);
          return (
            <button
              key={option.model.id}
              type="button"
              onClick={() => setPicked(on ? picked.filter((id) => id !== option.model.id) : [...picked, option.model.id])}
              className={`h-8 rounded-full px-3.5 text-[13px] transition-colors ${
                on ? "bg-accent/12 font-medium text-accent" : "bg-ink/[0.05] text-ink-muted hover:text-ink"
              }`}
            >
              {option.model.display_name}
            </button>
          );
        })}
        {picked.length === 0 && models.length > 0 && <span className="ml-1 text-[12.5px] text-ink-faint">Every model takes part unless you pick some.</span>}
      </div>
      {council.detail && <p className="mt-3 text-[13px] text-ink-muted">{council.detail}</p>}
      {council.error && <p className="mt-3 text-[13px] text-danger">{council.error}</p>}

      {labels.length === 0 && !council.running && (
        <Empty icon={Scale} title="Compare before you trust">
          Different models get different things wrong. When they agree you can relax; when they split, that is where to
          look closer.
        </Empty>
      )}

      <AnimatePresence>
        {council.verdict && (
          <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={BOUNCE} className="mt-5 rounded-3xl bg-accent/[0.07] p-5">
            <p className="mb-2 text-[13px] font-medium text-accent">
              Verdict · best first: {council.verdict.ranking.map((r) => r.label).join(", ") || "no ranking"}
            </p>
            {council.verdict.disagreements && <p className="mb-2 text-[14px] text-ink-muted">{council.verdict.disagreements}</p>}
            <Markdown text={council.verdict.synthesis} />
          </motion.section>
        )}
      </AnimatePresence>

      <div className="mt-5 grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
        {council.members.map((member) => {
          const answer = council.answers[member.label];
          const text = split(answer?.content || council.streaming[member.label] || "").answer;
          return (
            <article key={member.label} className="flex max-h-[420px] flex-col rounded-3xl border border-ink/[0.07] bg-surface p-4">
              <header className="mb-2 flex items-center gap-2 text-[13px]">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/[0.07] font-semibold text-ink">{member.label}</span>
                <span className="truncate font-medium text-ink">{nameOf(member.model_id)}</span>
                {answer && <span className="ml-auto text-ink-faint">{(answer.gen_ms / 1000).toFixed(1)}s</span>}
              </header>
              <div className="scroll-quiet min-h-0 overflow-y-auto text-[14px]">
                {answer?.error ? (
                  <p className="text-danger">{answer.error}</p>
                ) : text ? (
                  <Markdown text={text} />
                ) : (
                  <p className="shimmer font-medium">Thinking</p>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {council.agreement.length > 0 && (
        <div className="mt-6 flex flex-wrap gap-10">
          <AgreementMatrix cells={council.agreement} labels={labels} detail={council.agreementDetail} />
          {scores.length > 0 && (
            <div className="min-w-[220px]">
              <p className="mb-2 text-[13px] font-medium text-ink-muted">Wins so far</p>
              {scores.map((row) => (
                <p key={`${row.model_id}-${row.category}`} className="flex justify-between gap-4 py-0.5 text-[13px]">
                  <span className="truncate text-ink">{nameOf(row.model_id)}</span>
                  <span className="tabular-nums text-ink-faint">
                    {row.wins} of {row.appearances}
                  </span>
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </Sheet>
  );
}
