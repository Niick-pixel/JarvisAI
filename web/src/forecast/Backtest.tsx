// The track record: the same forecast run on stretches of your own history it was not shown, and
// scored against what happened. Read this before trusting the chart.
import type { BacktestResult } from "../api/types";
import { priceText } from "./CandleChart";

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="min-w-[150px] flex-1 rounded-3xl bg-ink/[0.04] p-4">
      <p className="text-[12.5px] text-ink-muted">{label}</p>
      <p className="mt-1 font-display text-[24px] font-semibold tabular-nums text-ink">{value}</p>
      <p className="mt-1 text-[12.5px] leading-snug text-ink-faint">{detail}</p>
    </div>
  );
}

function verdict(result: BacktestResult): string {
  if (result.windows < 8) return "Too few windows to say much either way.";
  if (result.skill > 0.05 && result.hit_rate > 0.55)
    return "On this data it did better than assuming no move. Still a small sample; markets change.";
  if (result.skill < -0.05) return "On this data it did worse than assuming the price stays put. Treat its forecasts as noise.";
  return "On this data it was about as good as assuming no move: no clear edge.";
}

export default function Backtest({ result, tick }: { result: BacktestResult; tick: number }) {
  const pct = (v: number) => `${Math.round(v * 100)}%`;
  return (
    <section className="mt-6">
      <h3 className="mb-2 text-[13px] font-semibold text-ink-muted">
        Track record · {result.windows} forecasts of {result.horizon * 5} minutes on your {result.symbol} history
      </h3>
      <div className="flex flex-wrap gap-3">
        <Stat label="Direction right" value={pct(result.hit_rate)} detail="A coin flip gets 50%." />
        <Stat
          label="Skill vs. no move"
          value={`${result.skill >= 0 ? "+" : ""}${pct(result.skill)}`}
          detail={`Typical miss ${priceText(result.mae_model, tick)} pts vs ${priceText(result.mae_naive, tick)} for "no move".`}
        />
        <Stat label="Inside the band" value={pct(result.coverage)} detail="Near 80% means the band is honest." />
      </div>
      <p className="mt-3 text-[14px] text-ink">{verdict(result)}</p>
    </section>
  );
}
