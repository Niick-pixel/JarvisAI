// The mark: a small glass sphere with a light inside that drifts. Quiet at rest, awake when
// Jarvis is thinking, and - in voice mode - breathing with whoever is speaking.
//
// Drawn in SVG, not WebGL: it is 20 pixels most of the time, and a second GPU context for 20
// pixels would be the opposite of the brief's rule about the GPU belonging to the model.
import { useEffect, useId, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { drive } from "../voice/level";

export type OrbState = "idle" | "thinking" | "listening" | "speaking";

const SPEED: Record<OrbState, number> = { idle: 0.25, thinking: 1.1, listening: 0.6, speaking: 0.8 };

export default function Orb({ size = 22, state = "idle" }: { size?: number; state?: OrbState }) {
  const raw = useId().replace(/:/g, "");
  const reduced = useReducedMotion();
  const light = useRef<SVGGElement>(null);
  const body = useRef<SVGGElement>(null);
  const reactive = state === "listening" || state === "speaking";

  useEffect(() => {
    if (reduced) return;
    let frame = 0;
    let last = performance.now();
    let t = Math.random() * 10;
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      t += dt * SPEED[state];
      const level = reactive ? drive.step(dt) : 0;
      // A Lissajous drift: never repeats visibly, never leaves the sphere.
      const x = Math.sin(t * 1.3) * 0.16 + Math.sin(t * 0.7) * 0.06;
      const y = Math.cos(t * 1.1) * 0.14 + Math.sin(t * 0.5) * 0.05;
      light.current?.setAttribute("transform", `translate(${x * 100} ${y * 100})`);
      const breathe = 1 + (reactive ? level * 0.14 : Math.sin(t * 2) * 0.012);
      body.current?.setAttribute("transform", `translate(50 50) scale(${breathe}) translate(-50 -50)`);
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [state, reactive, reduced]);

  const bright = state === "idle" ? 0.85 : 1;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden className="shrink-0 overflow-visible">
      <defs>
        <radialGradient id={`${raw}-base`} cx="38%" cy="32%" r="75%">
          <stop offset="0%" stopColor="rgb(var(--c-glow-a))" />
          <stop offset="55%" stopColor="rgb(var(--c-accent))" />
          <stop offset="100%" stopColor="rgb(var(--c-glow-b))" />
        </radialGradient>
        <radialGradient id={`${raw}-inner`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgb(var(--c-glow-c))" stopOpacity={0.95 * bright} />
          <stop offset="100%" stopColor="rgb(var(--c-glow-c))" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${raw}-rim`} cx="50%" cy="50%" r="50%">
          <stop offset="78%" stopColor="black" stopOpacity="0" />
          <stop offset="100%" stopColor="black" stopOpacity="0.28" />
        </radialGradient>
        <clipPath id={`${raw}-clip`}>
          <circle cx="50" cy="50" r="48" />
        </clipPath>
        <filter id={`${raw}-soft`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="7" />
        </filter>
      </defs>
      <g ref={body}>
        <g clipPath={`url(#${raw}-clip)`}>
          <circle cx="50" cy="50" r="48" fill={`url(#${raw}-base)`} />
          <g ref={light} filter={`url(#${raw}-soft)`}>
            <circle cx="58" cy="62" r="30" fill={`url(#${raw}-inner)`} />
          </g>
          <circle cx="50" cy="50" r="48" fill={`url(#${raw}-rim)`} />
          {/* The specular highlight: what makes it read as glass rather than a gradient dot. */}
          <ellipse cx="36" cy="28" rx="16" ry="10" fill="white" opacity="0.55" filter={`url(#${raw}-soft)`} />
        </g>
      </g>
    </svg>
  );
}
