// The light behind the composer, after Gemini: three soft colours that drift so slowly you notice
// them only when they change - and they change when Jarvis is working or listening.
//
// Plain CSS gradients with a blur. It costs nothing on the GPU the model is using, which is the
// point; the old full-screen shader did not.
import { motion, useReducedMotion } from "framer-motion";
import { resolve, useAppearance } from "../design/theme";
import tokens from "../design/tokens.json";

export type HaloState = "rest" | "busy" | "listening";

const OPACITY: Record<HaloState, number> = { rest: 0.55, busy: 1, listening: 1 };

export default function Halo({ state, placement }: { state: HaloState; placement: "center" | "bottom" }) {
  const reduced = useReducedMotion();
  const reduceEffects = useAppearance((s) => s.reduceEffects);
  // The peak alphas live in tokens.json, where scripts/contrast_check.py proves text stays legible
  // over all three stacked.
  const alpha = tokens.halo_alpha[resolve(useAppearance((s) => s.mode))];
  // Radial gradients rather than a blur filter: just as soft, far cheaper, and a large blur left a
  // faint ring at its edge on some renderers.
  const fill = (name: keyof typeof alpha) => ({
    background: `radial-gradient(closest-side, rgb(var(--c-${name}) / ${alpha[name]}), rgb(var(--c-${name}) / 0))`,
  });
  const still = reduced || reduceEffects;
  const drift = (seconds: number, x: number, y: number) =>
    still
      ? {}
      : {
          animate: { x: [0, x, -x * 0.6, 0], y: [0, -y, y * 0.7, 0], scale: [1, 1.08, 0.96, 1] },
          transition: { duration: state === "rest" ? seconds : seconds / 2.5, repeat: Infinity, ease: "easeInOut" as const },
        };
  const anchor = placement === "center" ? "top-1/2 -translate-y-1/2" : "bottom-[-120px]";

  return (
    <motion.div
      aria-hidden
      className={`pointer-events-none absolute left-1/2 ${anchor} -z-0 h-[520px] w-[900px] max-w-[140vw] -translate-x-1/2`}
      animate={{ opacity: OPACITY[state] * (placement === "bottom" ? 0.75 : 1) }}
      transition={{ type: "spring", stiffness: 60, damping: 20 }}
    >
      <motion.div
        className="absolute left-[10%] top-[5%] h-[90%] w-[60%] rounded-full"
        style={fill("glow-a")}
        {...drift(18, 40, 24)}
      />
      <motion.div
        className="absolute left-[34%] top-[12%] h-[85%] w-[56%] rounded-full"
        style={fill("glow-b")}
        {...drift(22, -36, 30)}
      />
      <motion.div
        className="absolute left-[24%] top-[30%] h-[75%] w-[48%] rounded-full"
        style={fill("glow-c")}
        {...drift(26, 30, -20)}
      />
    </motion.div>
  );
}
