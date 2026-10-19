// Live: bars arriving from NinjaTrader through the JarvisFeed indicator, the rolling forecast for
// each market, and the alerts. Until the feed is set up, the steps to set it up.
import { Download, Radio } from "lucide-react";
import { useEffect } from "react";
import { NINJASCRIPT_URL } from "../api/trading";
import type { LiveSymbol } from "../api/types";
import { useTrading } from "../store/trading";
import { Empty } from "../ui/controls";
import Alerts from "./Alerts";

const CLOCK = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});

function ago(seconds: number): string {
  if (seconds < 90) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} h ago`;
  return `${Math.round(seconds / 86400)} days ago`;
}

function Market({ m }: { m: LiveSymbol }) {
  const up = m.prob_up ?? null;
  return (
    <div className="min-w-[260px] flex-1 rounded-3xl border border-ink/[0.07] p-4">
      <div className="flex items-baseline gap-2">
        <p className="font-display text-[15px] font-semibold text-ink">
          {m.symbol}
        </p>
        <p className="text-[12px] text-ink-faint">{m.contract}</p>
        <span
          className={`ml-auto inline-flex items-center gap-1 text-[12px] ${m.stale ? "text-danger" : "text-success"}`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${m.stale ? "bg-danger" : "bg-success animate-pulse"}`}
          />
          {m.stale ? "No new bars" : "Live"}
        </span>
      </div>
      <p className="mt-1 font-display text-[26px] font-semibold tabular-nums text-ink">
        {m.last_close.toFixed(2)}
      </p>
      <p className="text-[12.5px] text-ink-faint">
        Bar ending {CLOCK.format(m.last_t * 1000)} ·{" "}
        {ago(Date.now() / 1000 - m.last_t)} · {m.bars_received} bars this
        session
      </p>
      {up !== null ? (
        <div className="mt-3">
          <div className="flex justify-between text-[12px] text-ink-muted">
            <span>Next hour: {Math.round(up * 100)}% of paths higher</span>
            {m.forecast_at && <span>{CLOCK.format(m.forecast_at)}</span>}
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-danger/25">
            <div
              className="h-full rounded-full bg-success"
              style={{ width: `${up * 100}%` }}
            />
          </div>
          <p className="mt-2 line-clamp-3 text-[12.5px] text-ink-muted">
            {m.forecast}
          </p>
        </div>
      ) : (
        <p className="mt-3 text-[12.5px] text-ink-faint">
          The rolling forecast starts with the next bars, once Kronos is set up.
        </p>
      )}
    </div>
  );
}

function SetupSteps({ folder }: { folder: string }) {
  return (
    <Empty icon={Radio} title="Connect NinjaTrader">
      <span className="block text-left">
        1.{" "}
        <a
          href={NINJASCRIPT_URL}
          download
          className="font-medium text-accent hover:underline"
        >
          Download JarvisFeed.cs <Download size={13} className="inline" />
        </a>{" "}
        and copy it to Documents\NinjaTrader 8\bin\Custom\Indicators.
        <br />
        2. In NinjaTrader: New › NinjaScript Editor, then press F5 to compile.
        <br />
        3. Open an ES or NQ chart on 5 Minute bars and add the JarvisFeed
        indicator.
        <br />
        It only writes finished bars to a text file in{" "}
        <span className="font-mono text-[12px]">{folder}</span> - it never
        trades and opens no connections.
      </span>
    </Empty>
  );
}

export default function Live() {
  const { live, refreshAll, refreshLive } = useTrading();
  useEffect(() => {
    void refreshAll().catch(() => undefined);
    const timer = window.setInterval(
      () => void refreshLive().catch(() => undefined),
      5000,
    );
    return () => window.clearInterval(timer);
  }, [refreshAll, refreshLive]);

  if (!live)
    return <p className="text-[13px] text-ink-faint">Checking the feed…</p>;
  return (
    <div>
      {live.symbols.length === 0 ? (
        <SetupSteps folder={live.folder} />
      ) : (
        <div className="flex flex-wrap gap-3">
          {live.symbols.map((m) => (
            <Market key={m.symbol} m={m} />
          ))}
        </div>
      )}
      {!live.forecasting && live.symbols.length > 0 && (
        <p className="mt-2 text-[12.5px] text-ink-faint">
          Rolling forecasts need Kronos - set it up in the Forecast tab.
        </p>
      )}
      <Alerts />
    </div>
  );
}
