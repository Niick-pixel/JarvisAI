// One device, as a tile you tap: lit up when it is on, quiet when it is off, "Not responding" when
// Home Assistant cannot reach it. A tap does the obvious thing; a light gets a dimmer, a speaker a
// volume, a thermostat its set point. Unlocking a door always asks first.
import type { LucideIcon } from "lucide-react";
import {
  Blinds,
  Bot,
  DoorClosed,
  DoorOpen,
  Droplets,
  Fan,
  Lightbulb,
  Lock,
  LockOpen,
  Minus,
  Play,
  Plus,
  Power,
  Radar,
  Sparkles,
  Speaker,
  Thermometer,
  ToggleLeft,
} from "lucide-react";
import type { Device, HomeAction } from "../api/types";
import { useHome } from "../store/home";

function icon(d: Device): LucideIcon {
  if (d.domain === "binary_sensor") {
    if (d.kind === "motion" || d.kind === "occupancy") return Radar;
    return d.state === "on" ? DoorOpen : DoorClosed;
  }
  if (d.domain === "sensor") return d.kind === "humidity" ? Droplets : Thermometer;
  const byDomain: Record<string, LucideIcon> = {
    light: Lightbulb,
    fan: Fan,
    cover: Blinds,
    climate: Thermometer,
    lock: d.state === "locked" ? Lock : LockOpen,
    media_player: Speaker,
    scene: Sparkles,
    script: Play,
    vacuum: Bot,
    input_boolean: ToggleLeft,
  };
  return byDomain[d.domain] ?? Power;
}

function active(d: Device): boolean {
  if (!d.available) return false;
  if (d.domain === "lock") return d.state === "unlocked";
  if (d.domain === "cover") return d.state === "open" || d.state === "opening";
  if (d.domain === "media_player") return d.state === "playing";
  if (d.domain === "climate") return d.state !== "off";
  if (d.domain === "vacuum") return d.state === "cleaning";
  return d.state === "on";
}

function describe(d: Device): string {
  if (!d.available) return "Not responding";
  const words: Record<string, string> = {
    on: "On",
    off: "Off",
    open: "Open",
    closed: "Closed",
    opening: "Opening",
    closing: "Closing",
    locked: "Locked",
    unlocked: "Unlocked",
    playing: "Playing",
    paused: "Paused",
    idle: "Idle",
    cleaning: "Cleaning",
    docked: "Docked",
  };
  if (d.domain === "binary_sensor") {
    if (d.kind === "motion" || d.kind === "occupancy") return d.state === "on" ? "Motion" : "Clear";
    return d.state === "on" ? "Open" : "Closed";
  }
  if (d.domain === "sensor") return `${d.current ?? d.state}${d.unit ? ` ${d.unit}` : ""}`;
  if (d.domain === "climate") {
    const now = d.current != null ? ` · ${d.current}° now` : "";
    const doing = d.detail ? d.detail[0]!.toUpperCase() + d.detail.slice(1) : "Set";
    return d.state === "off" ? `Off${now}` : `${doing} to ${d.target ?? "?"}°${now}`;
  }
  if (d.domain === "media_player" && d.detail) return d.detail;
  if (d.domain === "scene" || d.domain === "script" || d.domain === "button") return "Tap to run";
  const level = d.domain === "light" && d.state === "on" && d.level != null ? ` · ${d.level}%` : "";
  return `${words[d.state] ?? d.state}${level}`;
}

function primary(d: Device): HomeAction | null {
  if (d.actions.includes("toggle")) return "toggle";
  if (d.actions.includes("activate")) return "activate";
  if (d.actions.includes("press")) return "press";
  if (d.actions.includes("play_pause")) return "play_pause";
  if (d.domain === "lock") return d.state === "locked" ? "unlock" : "lock";
  if (d.domain === "cover") return d.state === "closed" ? "open" : "close";
  if (d.domain === "vacuum") return d.state === "cleaning" ? "return" : "start";
  return null;
}

export default function DeviceTile({ device }: { device: Device }) {
  const act = useHome((s) => s.act);
  const busy = useHome((s) => s.pending[device.entity_id]) ?? false;
  const Icon = icon(device);
  const lit = active(device);
  const tap = primary(device);
  const slider = device.state === "on" || device.state === "playing" ? (device.actions.includes("brightness") ? "brightness" : device.actions.includes("volume") ? "volume" : null) : null;

  const run = () => {
    if (!tap || busy || !device.available) return;
    if (tap === "unlock" && !window.confirm(`Unlock ${device.name}?`)) return;
    void act(device, tap);
  };

  return (
    <div
      className={`flex min-h-[112px] flex-col rounded-3xl p-4 transition-colors ${
        lit ? "bg-surface shadow-card" : "bg-ink/[0.045]"
      } ${device.available ? "" : "opacity-60"}`}
    >
      <button
        type="button"
        disabled={!tap || busy || !device.available}
        onClick={run}
        className="flex flex-1 flex-col items-start text-left disabled:cursor-default"
      >
        <span
          className={`flex h-9 w-9 items-center justify-center rounded-full transition-colors ${
            lit ? "bg-accent text-on-accent" : "bg-ink/[0.07] text-ink-muted"
          } ${busy ? "animate-pulse" : ""}`}
        >
          <Icon size={18} strokeWidth={1.9} />
        </span>
        <span className="mt-3 line-clamp-2 text-[14px] font-medium leading-snug text-ink">{device.name}</span>
        <span className="mt-0.5 line-clamp-1 text-[12.5px] text-ink-muted">{describe(device)}</span>
      </button>

      {slider && (
        <input
          type="range"
          min={1}
          max={100}
          defaultValue={device.level ?? 50}
          key={`${device.entity_id}-${device.level}`}
          aria-label={slider === "brightness" ? "Brightness" : "Volume"}
          onPointerUp={(e) => void act(device, slider, Number(e.currentTarget.value))}
          onKeyUp={(e) => void act(device, slider, Number(e.currentTarget.value))}
          className="mt-3 w-full accent-accent"
        />
      )}
      {device.domain === "climate" && device.target != null && device.available && (
        <div className="mt-3 flex items-center gap-2">
          {[
            { icon: Minus, delta: -0.5, label: "Cooler" },
            { icon: Plus, delta: 0.5, label: "Warmer" },
          ].map(({ icon: Step, delta, label }) => (
            <button
              key={label}
              type="button"
              aria-label={label}
              disabled={busy}
              onClick={() => void act(device, "temperature", (device.target ?? 20) + delta)}
              className="flex h-8 w-8 items-center justify-center rounded-full bg-ink/[0.07] text-ink transition-colors hover:bg-ink/[0.12]"
            >
              <Step size={15} strokeWidth={2} />
            </button>
          ))}
          <span className="ml-1 text-[13px] tabular-nums text-ink-muted">{device.target}°</span>
        </div>
      )}
    </div>
  );
}
