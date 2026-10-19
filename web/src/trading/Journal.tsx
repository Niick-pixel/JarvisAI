// Your trade journal: NinjaTrader's trade export in, the honest numbers out - and questions about
// it answered by the local model from your own trades, never from general advice.
import { ArrowUp, BookOpenCheck, FileUp, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Breakdown } from "../api/types";
import Markdown from "../chat/Markdown";
import { useTrading } from "../store/trading";
import { Button, Empty } from "../ui/controls";

const usd = (n: number) =>
  `${n < 0 ? "-" : ""}$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const SUGGESTIONS = [
  "Which hours lose me money?",
  "Am I better long or short?",
  "What happens after a losing trade?",
];

function Tile({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad";
}) {
  return (
    <div className="min-w-[120px] flex-1">
      <p className="text-[12px] text-ink-muted">{label}</p>
      <p
        className={`font-display text-[20px] font-semibold tabular-nums ${tone === "good" ? "text-success" : tone === "bad" ? "text-danger" : "text-ink"}`}
      >
        {value}
      </p>
    </div>
  );
}

function Bars({ title, rows }: { title: string; rows: Breakdown[] }) {
  const most = Math.max(1, ...rows.map((r) => Math.abs(r.net)));
  return (
    <div className="min-w-[240px] flex-1">
      <p className="mb-1.5 text-[12px] font-medium text-ink-muted">{title}</p>
      {rows.map((r) => (
        <div
          key={r.label}
          className="flex items-center gap-2 py-0.5 text-[12px]"
        >
          <span className="w-20 shrink-0 truncate text-ink-muted">
            {r.label}
          </span>
          <div className="h-2 flex-1 rounded-full bg-ink/[0.04]">
            <div
              className={`h-full rounded-full ${r.net >= 0 ? "bg-success" : "bg-danger"}`}
              style={{ width: `${(Math.abs(r.net) / most) * 100}%` }}
            />
          </div>
          <span
            className={`w-20 shrink-0 text-right tabular-nums ${r.net >= 0 ? "text-ink" : "text-danger"}`}
          >
            {usd(r.net)}
          </span>
          <span className="w-10 shrink-0 text-right tabular-nums text-ink-faint">
            {r.trades}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function Journal() {
  const {
    stats,
    trades,
    answer,
    asking,
    note,
    refreshAll,
    importJournal,
    clearJournal,
    ask,
  } = useTrading();
  const picker = useRef<HTMLInputElement>(null);
  const [question, setQuestion] = useState("");
  useEffect(() => void refreshAll().catch(() => undefined), [refreshAll]);
  const go = (q: string) => q.trim() && void ask(q.trim());

  return (
    <div>
      <div className="flex items-center gap-2">
        <p className="flex-1 text-[13px] text-ink-muted">
          {stats?.trades
            ? `${stats.trades} trades · ${stats.first.slice(0, 10)} to ${stats.last.slice(0, 10)}`
            : "No trades yet."}
        </p>
        {Boolean(stats?.trades) && (
          <Button
            small
            tone="ghost"
            icon={Trash2}
            onClick={() => void clearJournal()}
          >
            Clear
          </Button>
        )}
        <Button small icon={FileUp} onClick={() => picker.current?.click()}>
          Import trades
        </Button>
        <input
          ref={picker}
          type="file"
          multiple
          accept=".csv,.txt"
          className="hidden"
          onChange={(e) => {
            void importJournal(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
      </div>
      {note && <p className="mt-2 text-[12.5px] text-ink-muted">{note}</p>}

      {!stats?.trades ? (
        <Empty icon={BookOpenCheck} title="Import your trades">
          In NinjaTrader 8: Control Center › New › Trade Performance, pick the
          accounts and dates, choose Trades, then right-click the grid › Export.
          Import the .csv here - importing it again later only adds what is new.
        </Empty>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap gap-5">
            <Tile
              label="Net"
              value={usd(stats.net)}
              tone={stats.net >= 0 ? "good" : "bad"}
            />
            <Tile
              label="Win rate"
              value={`${Math.round(stats.win_rate * 100)}%`}
            />
            <Tile
              label="Avg win / loss"
              value={`${usd(stats.avg_win)} / ${usd(stats.avg_loss)}`}
            />
            <Tile
              label="Profit factor"
              value={stats.profit_factor?.toFixed(2) ?? "-"}
            />
            <Tile label="Per trade" value={usd(stats.expectancy)} />
            <Tile
              label="Worst drawdown"
              value={usd(-stats.max_drawdown)}
              tone="bad"
            />
          </div>
          <div className="mt-5 flex flex-wrap gap-6">
            <Bars title="By weekday" rows={stats.by_weekday ?? []} />
            <Bars title="By hour you entered" rows={stats.by_hour ?? []} />
          </div>
          <div className="mt-5 flex flex-wrap gap-6">
            <Bars title="Long or short" rows={stats.by_side ?? []} />
            <Bars title="By market" rows={stats.by_instrument ?? []} />
          </div>

          <div className="mt-6 flex items-end gap-2 rounded-3xl border border-ink/[0.08] bg-surface p-1.5 pl-4 shadow-card">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && go(question)}
              placeholder="Ask your journal - e.g. which hours lose me money?"
              className="min-w-0 flex-1 bg-transparent py-2 text-[14px] text-ink outline-none placeholder:text-ink-faint"
            />
            <button
              type="button"
              aria-label="Ask"
              disabled={asking || !question.trim()}
              onClick={() => go(question)}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-ink text-bg disabled:opacity-25"
            >
              <ArrowUp size={18} />
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setQuestion(s);
                  go(s);
                }}
                className="rounded-full bg-ink/[0.05] px-3 py-1 text-[12.5px] text-ink-muted hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
          {asking && (
            <p className="shimmer mt-3 text-[13.5px] font-medium">
              Reading your trades
            </p>
          )}
          {answer && (
            <div className="mt-3 rounded-2xl bg-ink/[0.03] p-4 text-[14px]">
              <Markdown text={answer.answer} />
            </div>
          )}

          <p className="mt-6 mb-1 text-[12px] font-medium text-ink-muted">
            Latest trades
          </p>
          <div className="text-[12.5px] tabular-nums">
            {trades.map((t) => (
              <div
                key={t.id}
                className="flex gap-3 border-b border-ink/[0.05] py-1"
              >
                <span className="w-36 text-ink-faint">
                  {t.entry_time.slice(0, 16)}
                </span>
                <span className="w-24 text-ink">{t.instrument}</span>
                <span className="w-12 text-ink-muted">{t.side}</span>
                <span className="w-24 text-ink-muted">
                  {t.qty} @ {t.entry_price}
                </span>
                <span
                  className={`ml-auto ${t.profit >= 0 ? "text-success" : "text-danger"}`}
                >
                  {usd(t.profit)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
