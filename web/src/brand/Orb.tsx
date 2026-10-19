// The mark: a helm with one red eye, after AUTO in WALL-E - six rounded handles on a dark ring
// around a white shell. Calm at rest; when Jarvis is thinking the ring turns and the eye
// brightens, and in voice mode the eye's glow swells with whoever is speaking.
//
// Drawn in SVG, not WebGL: it is 20 pixels most of the time, and a second GPU context for 20
// pixels would be the opposite of the brief's rule about the GPU belonging to the model.
// web/src/brand/jarvis.svg is the same drawing as a file (the app icon is rendered from it);
// change both together. Below 40 px the fine details are left out, as in the icon.
import { useEffect, useId, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { drive } from "../voice/level";

export type OrbState = "idle" | "thinking" | "listening" | "speaking";

const SPIN: Record<OrbState, number> = {
  idle: 0,
  thinking: 70,
  listening: 12,
  speaking: 18,
};
const HANDLES = [0, 60, 120, 180, 240, 300];
const WHITE = "#F4F6F9";
const DARK = "#2A2E36";
const EDGE = "#5A6170";
const BEZEL = "#1C1F25";

export default function Orb({
  size = 22,
  state = "idle",
}: {
  size?: number;
  state?: OrbState;
}) {
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
      glow.current?.setAttribute("r", "15");
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
      glow.current?.setAttribute("r", String(14 + level * 9));
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, [state, reactive, reduced]);

  const detailed = size >= 40;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      aria-hidden
      className="shrink-0 overflow-visible"
    >
      <defs>
        <radialGradient id={`${raw}-shell`} cx="40%" cy="35%" r="75%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="70%" stopColor="#EEF0F3" />
          <stop offset="100%" stopColor="#C9CED6" />
        </radialGradient>
        <radialGradient id={`${raw}-lens`} cx="44%" cy="42%" r="62%">
          <stop offset="0%" stopColor="#FFD2C2" />
          <stop offset="18%" stopColor="#FF6B5E" />
          <stop offset="58%" stopColor="#E0201B" />
          <stop offset="100%" stopColor="#7A0A0A" />
        </radialGradient>
        <radialGradient id={`${raw}-glow`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FF2A1F" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#FF2A1F" stopOpacity="0" />
        </radialGradient>
      </defs>

      <g ref={ring}>
        {HANDLES.map((deg) => (
          <rect
            key={deg}
            x="44.5"
            y="1.5"
            width="11"
            height="22"
            rx="5.5"
            fill={DARK}
            stroke={EDGE}
            strokeWidth="1.4"
            transform={`rotate(${deg} 50 50)`}
          />
        ))}
        {detailed &&
          HANDLES.map((deg) => (
            <rect
              key={deg}
              x="48.3"
              y="5.5"
              width="3.4"
              height="10.5"
              rx="1.7"
              fill={WHITE}
              transform={`rotate(${deg} 50 50)`}
            />
          ))}
        <circle
          cx="50"
          cy="50"
          r="33"
          fill={DARK}
          stroke={EDGE}
          strokeWidth="1.4"
        />
        {detailed && (
          <circle
            cx="50"
            cy="50"
            r="30"
            fill="none"
            stroke={WHITE}
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeDasharray="15.4 16"
            strokeDashoffset="7.7"
          />
        )}
      </g>

      <circle cx="50" cy="50" r="26" fill={`url(#${raw}-shell)`} />
      {detailed && (
        <path
          d="M50 24 V36 M50 64 V76"
          stroke={DARK}
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      )}
      <rect x="44" y="22.5" width="12" height="4.5" rx="1.6" fill={DARK} />
      <rect x="44" y="73" width="12" height="4.5" rx="1.6" fill={DARK} />
      <rect x="23" y="42" width="5.5" height="16" rx="2.4" fill={DARK} />
      <rect x="71.5" y="42" width="5.5" height="16" rx="2.4" fill={DARK} />

      <circle ref={glow} cx="50" cy="50" r="14" fill={`url(#${raw}-glow)`} />
      <circle cx="50" cy="50" r="15" fill={BEZEL} />
      <circle cx="50" cy="50" r="12.6" fill={`url(#${raw}-lens)`} />
      {detailed && (
        <circle
          cx="50"
          cy="50"
          r="10.2"
          fill="none"
          stroke="#9A0F0C"
          strokeWidth="0.8"
          opacity="0.7"
        />
      )}
      <circle cx="55.5" cy="44" r="2.5" fill="white" />
    </svg>
  );
}
