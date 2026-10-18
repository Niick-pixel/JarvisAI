// Forecast: ES and NQ five-minute bars from your NinjaTrader exports, forecast by Kronos on this PC,
// with the spread of what it thinks could happen and - one click away - how it has done before.
import { motion } from "framer-motion";
import { CandlestickChart, FileUp, MessageSquareText, Play, Target } from "lucide-react";
import { useEffect, useRef } from "react";
import Sheet from "../shell/Sheet";
import { HORIZONS, type Market, useForecast } from "../store/forecast";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";
import { Button, Empty, Segmented } from "../ui/controls";
import { GLIDE } from "../ui/motion";
import Backtest from "./Backtest";
import CandleChart, { priceText } from "./CandleChart";
import Setup from "./Setup";

const DAY = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "America/Chicago" });

function Tile({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="min-w-[150px] flex-1">
      <p className="text-[12.5px] text-ink-muted">{label}</p>
      <p className="font-display text-[22px] font-semibold tabular-nums text-ink">{value}</p>
      {detail && <p className="text-[12.5px] tabular-nums text-ink-faint">{detail}</p>}
    </div>
  );
}

export default function ForecastSheet() {
  const { symbol, horizon, status, series, job, setSymbol, setHorizon, refresh, importFiles, run, backtest, poll } =
    useForecast();
  const picker = useRef<HTMLInputElement>(null);
  const busy = job?.state === "loading" || job?.state === "running";

  useEffect(() => void refresh().catch(() => undefined), [refresh]);
  const packing = useForecast((s) => s.pack?.state === "downloading" || s.pack?.state === "verifying");
  useEffect(() => {
    if (!busy && !packing) return;
    let alive = true;
    const tick = async () => {
      const more = await poll().catch(() => false);
      if (alive && more) window.setTimeout(() => void tick(), 600);
    };
    void tick();
    return () => {
      alive = false;
    };
  }, [busy, packing, poll]);

  const info = series.find((s) => s.symbol === symbol);
  const ready = Boolean(status?.runtime && status.weights && info);
  const result = job?.forecast?.symbol === symbol ? job.forecast : null;
  const record = job?.backtest?.symbol === symbol ? job.backtest : null;
  const tick = result?.tick_size ?? 0.25;
  const end = result?.steps[result.steps.length - 1];

  const ask = () => {
    if (!result) return;
    useUi.getState().closeSheet();
    const session = useSession.getState();
    session.newChat();
    void session.send(
      `${result.summary}\n\nExplain what this forecast is saying in plain terms, how much weight it deserves, and what market conditions would make it wrong.`,
    );
  };

  return (
    <Sheet title="Forecast" subtitle="ES and NQ, five-minute bars, forecast by Kronos on this PC. Not trading advice." width={980}>
      <div className="flex flex-wrap items-center gap-2">
        <Segmented<Market> id="market" value={symbol} onChange={setSymbol} options={[{ value: "ES", label: "ES" }, { value: "NQ", label: "NQ" }]} />
        <Segmented<string>
          id="horizon"
          value={String(horizon)}
          onChange={(v) => setHorizon(Number(v))}
          options={HORIZONS.map((h) => ({ value: String(h.bars), label: h.label }))}
        />
        <div className="ml-auto flex gap-2">
          <Button small tone="ghost" icon={FileUp} onClick={() => picker.current?.click()}>
            Import
          </Button>
          <Button small tone="ghost" icon={Target} disabled={!ready || busy} onClick={() => void backtest()}>
            Track record
          </Button>
          <Button small tone="primary" icon={Play} disabled={!ready || busy} onClick={() => void run()}>
            Forecast
          </Button>
        </div>
        <input
          ref={picker}
          type="file"
          multiple
          accept=".txt,.csv"
          className="hidden"
          onChange={(e) => {
            void importFiles(Array.from(e.target.files ?? []));
            e.target.value = "";
          }}
        />
      </div>

      <p className="mt-3 text-[13px] text-ink-muted">
        {info
          ? `${info.bars.toLocaleString()} bars · ${DAY.format(info.first * 1000)} – ${DAY.format(info.last * 1000)}${info.contracts.length ? ` · contracts ${info.contracts.join(", ")}` : ""} · times ${info.zone_assumed ? "assumed" : "read as"} ${info.zone}`
          : `No ${symbol} data yet.`}
      </p>

      <Setup />

      {busy && job && (
        <div className="mt-5">
          <p className="text-[14px] text-ink">
            {job.state === "loading" ? "Loading Kronos…" : `${job.kind === "backtest" ? "Testing on your history" : "Sampling futures"} · step ${job.step} of ${job.total}`}
          </p>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/[0.07]">
            <motion.div className="h-full rounded-full bg-accent" animate={{ width: `${job.total ? (job.step / job.total) * 100 : 4}%` }} transition={GLIDE} />
          </div>
        </div>
      )}
      {job?.state === "failed" && job.symbol === symbol && <p className="mt-4 text-[14px] text-danger">{job.detail}</p>}

      {!info && (
        <Empty icon={CandlestickChart} title={`Import ${symbol} from NinjaTrader`}>
          In NinjaTrader 8: Tools › Historical Data › Export. Pick the {symbol} contract, Data type Last, Minute, and a few weeks of
          dates, then Import the .txt here. Add each contract you have and Jarvis rolls them into one series by volume.
        </Empty>
      )}

      {result && end && (
        <section className="mt-5">
          <div className="mb-4 flex flex-wrap gap-6">
            <Tile
              label={`Median in ${HORIZONS.find((h) => h.bars === result.horizon)?.label ?? `${result.horizon} bars`}`}
              value={priceText(end.c, tick)}
              detail={`${result.median_move >= 0 ? "+" : ""}${priceText(result.median_move, tick)} pts · ${Math.round(result.median_move / tick)} ticks${result.tick_value ? ` · ${result.median_move < 0 ? "-" : "+"}$${Math.abs(Math.round(result.median_move / tick) * result.tick_value).toFixed(2)}` : ""}`}
            />
            <Tile label="Paths ending higher" value={`${Math.round(result.prob_up * 100)}%`} detail="50% is no lean either way" />
            <Tile
              label="80% of paths ended between"
              value={`${priceText(end.p10, tick)} – ${priceText(end.p90, tick)}`}
            />
          </div>
          <CandleChart history={result.history} steps={result.steps} paths={result.paths} tick={tick} />
          {result.notes.map((note) => (
            <p key={note} className="mt-1 text-[12.5px] text-ink-faint">
              {note}
            </p>
          ))}
          <div className="mt-3 flex items-center gap-3">
            <Button small icon={MessageSquareText} onClick={ask}>
              Ask Jarvis about this
            </Button>
            <span className="text-[12.5px] text-ink-faint">
              {(result.elapsed_ms / 1000).toFixed(1)}s on this PC · {result.model}
            </span>
          </div>
        </section>
      )}

      {record && <Backtest result={record} tick={tick} />}
    </Sheet>
  );
}
