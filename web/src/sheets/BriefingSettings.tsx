// Settings → Morning briefing: when it comes, what it covers, and whether it is read aloud.
import { useEffect } from "react";
import type { BriefingSettings as Value } from "../api/types";
import { useBriefing } from "../store/briefing";
import { FIELD, Row, Segmented, Switch } from "../ui/controls";

type Section = Value["sections"][number];
const SECTIONS: { key: Section; label: string }[] = [
  { key: "markets", label: "ES and NQ" },
  { key: "home", label: "Home" },
  { key: "agents", label: "Agents" },
];

function next(at: number | null | undefined): string {
  if (!at) return "";
  const when = new Date(at);
  return ` Next: ${when.toLocaleDateString(undefined, { weekday: "long" })} at ${when.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}.`;
}

export default function BriefingSettings() {
  const { settings, load, save } = useBriefing();
  useEffect(() => void load().catch(() => undefined), [load]);
  if (!settings) return <Row title="Morning briefing" detail="Checking…" />;
  const toggle = (key: Section) =>
    void save({
      sections: settings.sections?.includes(key)
        ? settings.sections.filter((s) => s !== key)
        : [...(settings.sections ?? []), key],
    });

  return (
    <>
      <Row
        title="Morning briefing"
        detail={`Your forecasts, home and agent news, written up by the local model and waiting on Home.${settings.enabled ? next(settings.next_at) : ""}`}
      >
        <Switch label="Morning briefing" checked={settings.enabled ?? false} onChange={(enabled) => void save({ enabled })} />
      </Row>
      {settings.enabled && (
        <>
          <Row title="When">
            <div className="flex items-center gap-2">
              <input
                type="time"
                value={settings.time ?? "07:30"}
                onChange={(e) => e.target.value && void save({ time: e.target.value })}
                className={`${FIELD} !w-auto !py-1.5`}
              />
              <Segmented
                id="briefing-days"
                value={settings.days ?? "weekdays"}
                onChange={(days) => void save({ days })}
                options={[
                  { value: "weekdays", label: "Weekdays" },
                  { value: "daily", label: "Every day" },
                ]}
              />
            </div>
          </Row>
          <Row title="Covers">
            <div className="flex gap-1.5">
              {SECTIONS.map(({ key, label }) => {
                const on = settings.sections?.includes(key) ?? false;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggle(key)}
                    className={`rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors ${on ? "bg-accent/12 text-accent" : "bg-ink/[0.05] text-ink-muted hover:text-ink"}`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </Row>
          <Row title="Read it aloud" detail="The first time you open Jarvis after it is written.">
            <Switch label="Read it aloud" checked={settings.speak ?? false} onChange={(speak) => void save({ speak })} />
          </Row>
        </>
      )}
    </>
  );
}
