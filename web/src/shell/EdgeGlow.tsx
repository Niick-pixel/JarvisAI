// In a chat, after Gemini: a few small, faint pools of the brand colours drifting along the edges
// of the window - in and out, in a zigzag, each at its own pace and direction, so the pattern
// never visibly repeats. On Home the glow is the soft one behind the composer (Halo) instead.
//
// Cheap on purpose: each pool is one radial gradient moved by a CSS keyframe on transform only
// (positions in container units, so it follows the window's size), which the compositor runs.
// Reduce effects (or the OS's reduced motion) turns them off.
import { useReducedMotion } from "framer-motion";
import { useAppearance } from "../design/theme";

const POOLS = [
  { color: "glow-a", size: 300, seconds: 80, delay: 0, reverse: false },
  { color: "glow-b", size: 240, seconds: 110, delay: -37, reverse: true },
  { color: "glow-c", size: 270, seconds: 95, delay: -61, reverse: false },
];

export default function EdgeGlow({ busy }: { busy: boolean }) {
  const reduced = useReducedMotion();
  const off = useAppearance((s) => s.reduceEffects) || reduced;
  if (off) return null;
  return (
    <div aria-hidden className="edge-roam pointer-events-none absolute inset-0 z-0 overflow-hidden" style={{ opacity: busy ? 0.75 : 0.45 }}>
      {POOLS.map((p) => (
        <div
          key={p.color}
          className="absolute left-0 top-0 rounded-full will-change-transform"
          style={{
            width: p.size,
            height: p.size,
            margin: -p.size / 2,
            background: `radial-gradient(closest-side, rgb(var(--c-${p.color}) / 0.55), rgb(var(--c-${p.color}) / 0))`,
            animation: `edge-roam ${busy ? p.seconds / 2 : p.seconds}s ${p.delay}s linear infinite ${p.reverse ? "reverse" : "normal"}`,
          }}
        />
      ))}
    </div>
  );
}
