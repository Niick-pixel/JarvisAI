// A ring gauge: a 270° arc with rounded ends around a number, in the logo's red. Used by the
// activity bubble and the minimised widget. A pulsing dot says something is working in the
// background, whether or not it has a percentage to show.
export default function Gauge({
  value,
  text,
  unit,
  busy,
  size = 36,
  onDark = false,
}: {
  value: number;
  text: string;
  unit?: string;
  busy?: boolean;
  size?: number;
  /** On the minimised widget's dark tile, whatever the app's theme. */
  onDark?: boolean;
}) {
  const stroke = size * 0.11;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const arc = circumference * 0.75;
  const filled = (arc * Math.max(0, Math.min(100, value))) / 100;
  const small = size < 48;
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-[135deg]" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={onDark ? "rgba(255,255,255,0.14)" : "rgb(var(--c-ink) / 0.12)"} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={`${arc} ${circumference}`} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#E5322D"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      {busy && <span className="absolute right-0 top-0 h-2 w-2 animate-pulse rounded-full bg-[#E5322D]" />}
      <span className="absolute flex flex-col items-center leading-none">
        <span className={`font-semibold tabular-nums ${onDark ? "text-white" : "text-ink"} ${small ? "text-[11px]" : "text-[26px]"}`}>{text}</span>
        {unit && !small && <span className={`mt-1 text-[10px] uppercase tracking-wide ${onDark ? "text-white/55" : "text-ink-faint"}`}>{unit}</span>}
      </span>
    </span>
  );
}
