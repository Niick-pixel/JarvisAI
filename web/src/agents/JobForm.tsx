// A new routine. The schedule is chosen in words and written as cron underneath; the tool list is
// the backend's own catalogue, so what you tick is exactly what the model is told it has.
import { useState } from "react";
import type { ToolInfo } from "../api/types";
import { useAgents } from "../store/agents";
import { Button, FIELD, Segmented, Switch } from "../ui/controls";

type Every = "day" | "weekdays" | "week" | "hour" | "custom";
const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function clock(h: number, m: number): string {
  return new Date(2000, 0, 1, h, m).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

/** Cron, read back as a sentence where it is one of the shapes this form writes. */
export function describe(cron: string): string {
  const [m, h, dom, mon, dow] = cron.trim().split(/\s+/);
  if (dom !== "*" || mon !== "*") return cron;
  if (h === "*" && /^\d+$/.test(m ?? "") && dow === "*") return "Every hour";
  if (!/^\d+$/.test(m ?? "") || !/^\d+$/.test(h ?? "")) return cron;
  const at = clock(Number(h), Number(m));
  if (dow === "*") return `Every day at ${at}`;
  if (dow === "1-5") return `Weekdays at ${at}`;
  if (/^[0-6]$/.test(dow ?? "")) return `${DAYS[Number(dow)]}s at ${at}`;
  return cron;
}

function build(every: Every, time: string, day: number, custom: string): string {
  const [h, m] = time.split(":").map(Number);
  if (every === "hour") return "0 * * * *";
  if (every === "custom") return custom.trim();
  const dow = every === "day" ? "*" : every === "weekdays" ? "1-5" : String(day);
  return `${m ?? 0} ${h ?? 9} * * ${dow}`;
}

export default function JobForm({ tools, onDone }: { tools: ToolInfo[]; onDone: () => void }) {
  const create = useAgents((s) => s.create);
  const [name, setName] = useState("");
  const [prompt, setPrompt] = useState("");
  const [every, setEvery] = useState<Every>("day");
  const [time, setTime] = useState("09:00");
  const [day, setDay] = useState(1);
  const [custom, setCustom] = useState("0 19 * * *");
  const [workspace, setWorkspace] = useState("");
  const [chosen, setChosen] = useState<string[]>([]);
  const ready = Boolean(name.trim() && prompt.trim());

  const submit = async () => {
    if (!ready) return;
    const cron = build(every, time, day, custom);
    const body = { name: name.trim(), cron, prompt: prompt.trim(), tools: chosen, workspace: workspace.trim(), enabled: true };
    if (await create(body)) onDone();
  };

  return (
    <div className="space-y-4">
      <input className={FIELD} placeholder="Name it - e.g. Morning briefing" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      <textarea
        className={`${FIELD} min-h-28 resize-y`}
        placeholder="What should it do? Ask the way you'd ask a person."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <div>
        <p className="mb-2 text-[13px] font-medium text-ink-muted">When</p>
        <Segmented
          id="every"
          value={every}
          onChange={setEvery}
          options={[
            { value: "day", label: "Daily" },
            { value: "weekdays", label: "Weekdays" },
            { value: "week", label: "Weekly" },
            { value: "hour", label: "Hourly" },
            { value: "custom", label: "Custom" },
          ]}
        />
        <div className="mt-2 flex gap-2">
          {every === "week" && (
            <select value={day} onChange={(e) => setDay(Number(e.target.value))} className={`${FIELD} w-44`}>
              {DAYS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
          )}
          {every !== "hour" && every !== "custom" && (
            <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className={`${FIELD} w-36`} />
          )}
          {every === "custom" && (
            <input value={custom} onChange={(e) => setCustom(e.target.value)} className={`${FIELD} font-mono`} title="minute hour day month weekday" />
          )}
        </div>
      </div>
      <div>
        <p className="mb-1 text-[13px] font-medium text-ink-muted">What it may use</p>
        <div className="divide-y divide-ink/[0.06]">
          {tools.map((tool) => (
            <div key={tool.name} className="flex items-center gap-4 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="text-[14px] text-ink">
                  {tool.name}
                  {tool.side_effect && <span className="ml-2 text-[12px] text-ink-faint">asks you first</span>}
                </p>
                <p className="text-[12.5px] leading-snug text-ink-faint">{tool.summary}</p>
              </div>
              <Switch
                label={tool.name}
                checked={chosen.includes(tool.name)}
                onChange={(on) => setChosen((c) => (on ? [...c, tool.name] : c.filter((n) => n !== tool.name)))}
              />
            </div>
          ))}
        </div>
      </div>
      <input
        className={FIELD}
        placeholder="A folder it may write in (leave empty and it can't write anywhere)"
        value={workspace}
        onChange={(e) => setWorkspace(e.target.value)}
      />
      <div className="flex justify-end gap-2">
        <Button tone="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button tone="primary" onClick={() => void submit()} disabled={!ready}>
          Create routine
        </Button>
      </div>
    </div>
  );
}
