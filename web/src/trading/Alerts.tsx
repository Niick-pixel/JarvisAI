// Alert rules, and what they have said. A rule rings once when it becomes true and again only
// after it has stopped being true - so price sitting on a level does not ring every bar.
import { BellRing, Trash2 } from "lucide-react";
import { useState } from "react";
import type { AlertRule } from "../api/types";
import { useTrading } from "../store/trading";
import { Button, FIELD, IconButton, Switch } from "../ui/controls";

type Kind = AlertRule["kind"];
const KINDS: { kind: Kind; label: string; unit: string; example: number }[] = [
  { kind: "above", label: "Closes above", unit: "", example: 5850 },
  { kind: "below", label: "Closes below", unit: "", example: 5750 },
  {
    kind: "prob_up",
    label: "Forecast leans up at least",
    unit: "%",
    example: 70,
  },
  {
    kind: "prob_down",
    label: "Forecast leans down at least",
    unit: "%",
    example: 70,
  },
  { kind: "range", label: "Hour's range reaches", unit: "points", example: 30 },
  { kind: "stale", label: "Feed goes quiet", unit: "", example: 15 },
];

function describe(rule: AlertRule): string {
  const k = KINDS.find((x) => x.kind === rule.kind);
  if (rule.kind === "stale")
    return `${rule.symbol}: no bars for 15 minutes while the market is open`;
  return `${rule.symbol}: ${k?.label.toLowerCase()} ${rule.value}${k?.unit ? ` ${k.unit}` : ""}`;
}

export default function Alerts() {
  const { live, rules, addRule, removeRule, speakAlerts, setSpeakAlerts } =
    useTrading();
  const [symbol, setSymbol] = useState("ES");
  const [kind, setKind] = useState<Kind>("above");
  const [value, setValue] = useState("");
  const chosen = KINDS.find((k) => k.kind === kind);
  const add = () => {
    const number = kind === "stale" ? 15 : Number(value);
    if (!Number.isFinite(number) || (kind !== "stale" && !value.trim())) return;
    void addRule({ symbol, kind, value: number }).then(() => setValue(""));
  };

  return (
    <section className="mt-6">
      <div className="mb-2 flex items-center gap-2">
        <h3 className="flex-1 text-[13px] font-semibold text-ink-muted">
          Alerts
        </h3>
        <span className="text-[12.5px] text-ink-faint">Read them aloud</span>
        <Switch
          label="Read alerts aloud"
          checked={speakAlerts}
          onChange={setSpeakAlerts}
        />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className={`${FIELD} !w-24 !py-1.5`}
        >
          <option>ES</option>
          <option>NQ</option>
        </select>
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as Kind)}
          className={`${FIELD} !w-auto !py-1.5`}
        >
          {KINDS.map((k) => (
            <option key={k.kind} value={k.kind}>
              {k.label}
            </option>
          ))}
        </select>
        {kind !== "stale" && (
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            inputMode="decimal"
            placeholder={`${chosen?.example ?? ""}${chosen?.unit ? ` ${chosen.unit}` : ""}`}
            className={`${FIELD} !w-32 !py-1.5`}
          />
        )}
        <Button small icon={BellRing} onClick={add}>
          Add alert
        </Button>
      </div>
      <div className="mt-2 -mx-2">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="group flex items-center gap-2 rounded-2xl px-2 py-1.5 hover:bg-ink/[0.03]"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${rule.armed ? "bg-success" : "bg-ink/25"}`}
              title={rule.armed ? "Armed" : "Rang - waits to reset"}
            />
            <span className="flex-1 text-[13.5px] text-ink">
              {describe(rule)}
            </span>
            <IconButton
              icon={Trash2}
              label="Remove alert"
              size={28}
              onClick={() => void removeRule(rule.id)}
            />
          </div>
        ))}
      </div>
      {live && live.events.length > 0 && (
        <div className="mt-3 rounded-2xl bg-ink/[0.03] p-3">
          <p className="mb-1 text-[12px] font-medium text-ink-muted">Recent</p>
          {live.events.slice(0, 6).map((e) => (
            <p key={e.id} className="text-[12.5px] text-ink">
              <span className="mr-2 tabular-nums text-ink-faint">
                {new Date(e.created_at).toLocaleTimeString(undefined, {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </span>
              {e.message}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
