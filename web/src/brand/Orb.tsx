// The mark: a white sphere with one red lens, held in a ring with six handles - a helm. Calm at
// rest; when Jarvis is thinking the ring turns and the lens brightens, and in voice mode the lens
// swells with whoever is speaking.
//
// Drawn in SVG, not WebGL: it is 20 pixels most of the time, and a second GPU context for 20
// pixels would be the opposite of the brief's rule about the GPU belonging to the model.
// packaging/make_icon.py draws the same shapes for the app icon; change both together.
import { useEffect, useId, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { drive } from "../voice/level";

export type OrbState = "idle" | "thinking" | "listening" | "speaking";

const SPIN: Record<OrbState, number> = { idle: 0, thinking: 70, listening: 12, speaking: 18 };
const HANDLES = [30, 90, 150, 210, 270, 330];
const WHITE = "#F4F6F9";
const DARK = "#2A2E36";

export default function Orb({ size = 22, state = "idle" }: { size?: number; state?: OrbState }) {
  const raw = useId().replace(/:/g, "");
  const reduced = useReducedMotion();
  const ring = useRef<SVGGElement>(null);
  const glow = useRef<SVGCircleElement>(null);
  const reactive = state === "listening" || state === "speaking";

  useEffect(() => {
    // At rest it is still: a frame loop per mark, all day, for motion nobody is watching is
    // exactly the kind of cost that makes a window feel heavy.
    if (reduced || state === "idle") {
      ring.current?.setAttribute("transform", "");
      glow.current?.setAttribute("r", "14");
      return;
    }
    let frame = 0;
    let last = performance.now();
    let angle = 0;
    let t = 0;
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      t += dt;
      angle = (angle + dt * SPIN[state]) % 360;
      ring.current?.setAttribute("transform", `rotate(${angle} 50 50)`);
      const level = reactive ? drive.step(dt) : 0.5 + Math.sin(t * 4) * 0.5;
      glow.current?.setAttribute("r", String(13 + level * 7));
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [state, reactive, reduced]);

  // White parts need an edge to exist on the light theme; on dark it reads as a soft shadow.
  const edge = "rgb(var(--c-ink) / 0.38)";
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden className="shrink-0 overflow-visible">
      <defs>
        <radialGradient id={`${raw}-shell`} cx="38%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="65%" stopColor="#E9ECF1" />
          <stop offset="100%" stopColor="#BFC5CF" />
        </radialGradient>
        <radialGradient id={`${raw}-lens`} cx="42%" cy="38%" r="60%">
          <stop offset="0%" stopColor="#FF6B5E" />
          <stop offset="55%" stopColor="#E0201B" />
          <stop offset="100%" stopColor="#7A0A0A" />
        </radialGradient>
        <radialGradient id={`${raw}-glow`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FF2A1F" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#FF2A1F" stopOpacity="0" />
        </radialGradient>
      </defs>

      <g ref={ring}>
        <circle cx="50" cy="50" r="38" fill="none" stroke={edge} strokeWidth="10.5" />
        <circle cx="50" cy="50" r="38" fill="none" stroke={WHITE} strokeWidth="7.5" />
        {HANDLES.map((deg) => (
          <g key={deg} transform={`rotate(${deg} 50 50)`}>
            <rect x="84" y="45" width="15" height="10" rx="5" fill={WHITE} stroke={edge} strokeWidth="1.5" />
            <rect x="84" y="45.6" width="5" height="8.8" rx="1.5" fill={DARK} />
          </g>
        ))}
      </g>

      <ellipse cx="50" cy="51" rx="26" ry="28" fill={`url(#${raw}-shell)`} stroke={edge} strokeWidth="1.6" />
      {/* The seam that splits the shell in two, and the slot above the lens. */}
      <path d="M50 23.5 V35 M50 68 V78.5" stroke={DARK} strokeWidth="2.4" strokeLinecap="round" />
      <rect x="37" y="32" width="10" height="2.6" rx="1.3" fill={DARK} opacity="0.75" />

      <circle ref={glow} cx="50" cy="52" r="14" fill={`url(#${raw}-glow)`} />
      <circle cx="50" cy="52" r="12" fill="#1C1F25" />
      <circle cx="50" cy="52" r="8.8" fill={`url(#${raw}-lens)`} />
      <circle cx="46.8" cy="48.8" r="2.3" fill="white" opacity="0.8" />
    </svg>
  );
}
