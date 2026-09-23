// This PC, live (BRIEF.md 4.10): memory on the graphics card, how hard it is working, and how
// many tokens it has written for you - with what that would have cost from a hosted API.
// Fields the driver does not expose show a dash.
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HudSample, LifetimeCounters } from "../api/types";
import { useSession } from "../store/session";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-ink/[0.035] px-4 py-3">
      <p className="text-[18px] font-semibold tabular-nums tracking-tight text-ink">{value}</p>
      <p className="text-[12px] text-ink-faint">{label}</p>
    </div>
  );
}

const gb = (mb: number) => `${(mb / 1024).toFixed(1)} GB`;
const dash = (v: number | null | undefined, unit: string) => (v == null ? "-" : `${Math.round(v)}${unit}`);

export default function Machine() {
  const [sample, setSample] = useState<HudSample | null>(null);
  const [counters, setCounters] = useState<LifetimeCounters | null>(null);
  const tps = useSession((s) => s.tps);

  useEffect(() => {
    const source = new EventSource("/api/hud/stream");
    source.addEventListener("hud", (event) => setSample(JSON.parse((event as MessageEvent<string>).data) as HudSample));
    void api.hudCounters().then(setCounters).catch(() => undefined);
    return () => source.close();
  }, []);

  const gpu = sample?.gpu;
  return (
    <div className="grid grid-cols-2 gap-2 py-2 sm:grid-cols-3">
      <Stat label="Graphics memory" value={gpu ? `${gb(gpu.vram_used_mb)} / ${gb(gpu.vram_total_mb)}` : "No GPU found"} />
      <Stat label="GPU busy" value={dash(gpu?.utilization_pct, "%")} />
      <Stat label="GPU temperature" value={dash(gpu?.temperature_c, "°C")} />
      <Stat label="System memory" value={sample ? `${gb(sample.ram_used_mb)} / ${gb(sample.ram_total_mb)}` : "-"} />
      <Stat label="Last answer speed" value={tps > 0 ? `${tps.toFixed(1)} tok/s` : "-"} />
      {counters && <Stat label="Tokens written, ever" value={counters.tokens_generated.toLocaleString()} />}
      {counters && (
        <div className="col-span-2 rounded-2xl bg-success/[0.08] px-4 py-3 sm:col-span-3">
          <p className="text-[18px] font-semibold tabular-nums tracking-tight text-success">${counters.cost_avoided_usd.toFixed(2)}</p>
          <p className="text-[12px] text-ink-faint">
            what those tokens would have cost from a hosted API, at ${counters.rate_per_million_usd} per million
          </p>
        </div>
      )}
    </div>
  );
}
