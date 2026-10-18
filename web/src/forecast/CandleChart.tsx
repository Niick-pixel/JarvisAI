// The forecast chart: the last twelve hours of real candles, then the forecast - median candles,
// the faint sampled paths, and the band 80% of them stayed inside. Bars are spaced evenly, the way
// trading charts draw them, so the overnight halt does not leave a hole.
import { useEffect, useMemo, useRef, useState } from "react";
import type { Candle, ForecastStep } from "../api/types";

const HEIGHT = 340;
const PAD = { top: 12, right: 64, bottom: 26, left: 8 };
const CT = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/Chicago",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const CT_DAY = new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", weekday: "short" });

function niceStep(range: number): number {
  const raw = range / 5;
  const power = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= raw) ?? raw;
}

export function priceText(value: number, tick: number): string {
  const rounded = Math.round(value / tick) * tick;
  return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function CandleChart({
  history,
  steps,
  paths,
  tick,
}: {
  history: Candle[];
  steps: ForecastStep[];
  paths: number[][];
  tick: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => entry && setWidth(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const total = history.length + steps.length;
  const plotW = Math.max(100, width - PAD.left - PAD.right);
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotW / total;
  const x = (i: number) => PAD.left + slot * (i + 0.5);

  const [lo, hi] = useMemo(() => {
    const values = [
      ...history.flatMap((c) => [c.l, c.h]),
      ...steps.flatMap((s) => [s.l, s.h, s.p10, s.p90]),
    ];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const pad = (max - min) * 0.06 || tick * 4;
    return [min - pad, max + pad];
  }, [history, steps, tick]);
  const y = (price: number) => PAD.top + ((hi - price) / (hi - lo)) * plotH;

  const step = niceStep(hi - lo);
  const levels: number[] = [];
  for (let level = Math.ceil(lo / step) * step; level <= hi; level += step) levels.push(level);

  const now = history.length - 1;
  const last = history[now];
  if (!last) return null;
  const bandTop = [`${x(now)},${y(last.c)}`, ...steps.map((s, i) => `${x(now + 1 + i)},${y(s.p90)}`)];
  const bandBottom = [...steps.map((s, i) => `${x(now + 1 + i)},${y(s.p10)}`)].reverse();
  const bodyW = Math.max(1, slot * 0.62);
  const labelEvery = Math.max(1, Math.ceil(total / Math.max(2, plotW / 90)));

  const all: (Candle | ForecastStep)[] = [...history, ...steps];
  const shown = hover !== null ? all[hover] : null;

  return (
    <div ref={box} className="relative w-full select-none">
      <p className="mb-1 h-5 text-[12.5px] tabular-nums text-ink-muted">
        {shown
          ? `${CT_DAY.format(shown.t * 1000)} ${CT.format(shown.t * 1000)} CT${hover !== null && hover > now ? " · forecast" : ""}  ·  O ${priceText(shown.o, tick)}  H ${priceText(shown.h, tick)}  L ${priceText(shown.l, tick)}  C ${priceText(shown.c, tick)}`
          : "Hover a bar for its prices. Times are exchange time (Chicago)."}
      </p>
      <svg
        width={width}
        height={HEIGHT}
        className="block"
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const left = e.currentTarget.getBoundingClientRect().left;
          const i = Math.floor((e.clientX - left - PAD.left) / slot);
          setHover(i >= 0 && i < total ? i : null);
        }}
      >
        {levels.map((level) => (
          <g key={level}>
            <line x1={PAD.left} x2={PAD.left + plotW} y1={y(level)} y2={y(level)} className="stroke-ink/[0.06]" />
            <text x={PAD.left + plotW + 8} y={y(level) + 4} className="fill-ink-faint text-[11px] tabular-nums">
              {priceText(level, tick)}
            </text>
          </g>
        ))}

        {all.map((bar, i) =>
          i % labelEvery === Math.floor(labelEvery / 2) ? (
            <text key={bar.t} x={x(i)} y={HEIGHT - 8} textAnchor="middle" className="fill-ink-faint text-[11px] tabular-nums">
              {CT.format(bar.t * 1000)}
            </text>
          ) : null,
        )}

        <rect x={x(now) + slot / 2} y={PAD.top} width={plotW - x(now) - slot / 2 + PAD.left} height={plotH} className="fill-accent/[0.035]" />
        <line x1={x(now) + slot / 2} x2={x(now) + slot / 2} y1={PAD.top} y2={PAD.top + plotH} strokeDasharray="3 4" className="stroke-ink/25" />

        <polygon points={[...bandTop, ...bandBottom, `${x(now)},${y(last.c)}`].join(" ")} className="fill-accent/[0.13]" />
        {paths.map((path, p) => (
          <polyline
            key={p}
            points={[`${x(now)},${y(last.c)}`, ...path.map((v, i) => `${x(now + 1 + i)},${y(v)}`)].join(" ")}
            fill="none"
            strokeWidth={1}
            className="stroke-accent/25"
          />
        ))}

        {history.map((c, i) => {
          const up = c.c >= c.o;
          const tone = up ? "stroke-success fill-success" : "stroke-danger fill-danger";
          return (
            <g key={c.t} className={`${tone} ${hover === i ? "opacity-100" : "opacity-90"}`}>
              <line x1={x(i)} x2={x(i)} y1={y(c.h)} y2={y(c.l)} strokeWidth={1} />
              <rect x={x(i) - bodyW / 2} y={y(Math.max(c.o, c.c))} width={bodyW} height={Math.max(1, Math.abs(y(c.o) - y(c.c)))} />
            </g>
          );
        })}

        {steps.map((s, k) => {
          const i = now + 1 + k;
          return (
            <g key={s.t} className="stroke-accent">
              <line x1={x(i)} x2={x(i)} y1={y(s.h)} y2={y(s.l)} strokeWidth={1} />
              <rect
                x={x(i) - bodyW / 2}
                y={y(Math.max(s.o, s.c))}
                width={bodyW}
                height={Math.max(1, Math.abs(y(s.o) - y(s.c)))}
                strokeWidth={1.2}
                className={s.c >= s.o ? "fill-surface" : "fill-accent/60"}
              />
            </g>
          );
        })}

        <g transform={`translate(${PAD.left + plotW + 2} ${y(last.c) - 9})`}>
          <rect width={PAD.right - 4} height={18} rx={5} className="fill-ink" />
          <text x={6} y={13} className="fill-bg text-[11px] font-medium tabular-nums">
            {priceText(last.c, tick)}
          </text>
        </g>
        {hover !== null && (
          <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + plotH} className="stroke-ink/20" />
        )}
      </svg>
    </div>
  );
}
