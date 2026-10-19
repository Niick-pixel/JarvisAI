// Colour that drifts slowly around the edge of the window, after Gemini: the brand's three glow
// colours on a wheel, turning once a minute, seen only through a soft frame at the border.
//
// Cheap on purpose. The wheel is a single conic gradient rotated by a CSS animation - transform
// only, so the compositor runs it - and the frame is a static mask. Nothing is redrawn per frame on
// the main thread, which matters in an app whose GPU belongs to the model. Reduce effects (or the
// OS's reduced motion) keeps the frame and stops the turning.
import { useReducedMotion } from "framer-motion";
import { useAppearance } from "../design/theme";

export default function EdgeGlow({ busy }: { busy: boolean }) {
  const reduced = useReducedMotion();
  const still = useAppearance((s) => s.reduceEffects) || reduced;
  return (
    <div
      aria-hidden
      className="edge-glow pointer-events-none absolute inset-0 z-0 overflow-hidden"
      style={{ opacity: busy ? 1 : 0.8 }}
    >
      <div
        className="absolute left-1/2 top-1/2 aspect-square w-[150vmax] -translate-x-1/2 -translate-y-1/2 will-change-transform"
        style={{
          background:
            "conic-gradient(from 0deg, rgb(var(--c-glow-a) / 0.55), rgb(var(--c-glow-b) / 0.5), rgb(var(--c-glow-c) / 0.45), rgb(var(--c-glow-a) / 0) 62%, rgb(var(--c-glow-b) / 0.5) 80%, rgb(var(--c-glow-a) / 0.55))",
          animation: still
            ? undefined
            : `edge-turn ${busy ? 24 : 60}s linear infinite`,
        }}
      />
    </div>
  );
}
