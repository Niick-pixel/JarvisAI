// Settings, in the order people look for things: you, how it looks, how it answers, voice, this
// PC, and - last and off by default - the instruments for people who like instruments.
import { Download, Monitor, Moon, Sun } from "lucide-react";
import type { ReactNode } from "react";
import type { EngineStatus } from "../api/types";
import { type ThemeMode, useAppearance } from "../design/theme";
import Sheet from "../shell/Sheet";
import { useDownloads } from "../store/downloads";
import { useLibrary } from "../store/library";
import { type ThinkMode, useUi } from "../store/ui";
import { useVoice } from "../store/voice";
import { Button, FIELD, Row, Segmented, Switch } from "../ui/controls";
import VoicePack from "../voice/VoicePack";
import Machine from "./Machine";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6 first:mt-1">
      <h3 className="mb-1 text-[13px] font-semibold text-ink-muted">{title}</h3>
      <div className="divide-y divide-ink/[0.06]">{children}</div>
    </section>
  );
}

function Engine({ title, engine }: { title: string; engine?: EngineStatus }) {
  if (!engine) return <Row title={title} detail="Checking…" />;
  if (engine.available) {
    return <Row title={title} detail={`Ready - runs on this PC (${engine.engine}, ${engine.device})`} />;
  }
  const fix = engine.fix && !engine.downloadable ? ` ${engine.fix}` : "";
  return <Row title={title} detail={`${engine.reason}${fix}`} />;
}

export default function SettingsSheet() {
  const { mode, setMode, reduceEffects, setReduceEffects } = useAppearance();
  const { name, setName, think, setThink, devTools, setDevTools } = useUi();
  const voice = useVoice((s) => s.status);
  const { models, selectedModelId } = useLibrary();
  const current = models.find((m) => m.model.id === selectedModelId) ?? models.find((m) => m.recommended);

  return (
    <Sheet title="Settings" width={680}>
      <Section title="You">
        <Row title="Your name" detail="So Jarvis can greet you.">
          <div className="w-56 shrink-0">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className={FIELD} />
          </div>
        </Row>
      </Section>

      <Section title="Appearance">
        <Row title="Theme">
          <Segmented<ThemeMode>
            id="theme"
            value={mode}
            onChange={setMode}
            options={[
              { value: "light", label: "Light", icon: Sun },
              { value: "dark", label: "Dark", icon: Moon },
              { value: "system", label: "Auto", icon: Monitor },
            ]}
          />
        </Row>
        <Row title="Reduce effects" detail="Keep the glow still. Also gives a little more of the GPU back to the model.">
          <Switch label="Reduce effects" checked={reduceEffects} onChange={setReduceEffects} />
        </Row>
      </Section>

      <Section title="Answers">
        <Row title="Thinking" detail="Whether reasoning models think before they answer. You can change it per message too.">
          <Segmented<ThinkMode>
            id="think"
            value={think}
            onChange={setThink}
            options={[
              { value: "auto", label: "Auto" },
              { value: "on", label: "Think" },
              { value: "off", label: "Fast" },
            ]}
          />
        </Row>
        <Row
          title={current ? current.model.display_name : "No model yet"}
          detail={current?.budget?.explanation ?? current?.reason ?? "Download one to get started."}
        >
          <Button small icon={Download} onClick={() => void useDownloads.getState().show()}>
            Models
          </Button>
        </Row>
      </Section>

      <Section title="Voice">
        <Engine title="Dictation" engine={voice?.stt} />
        <Engine title="Reading aloud" engine={voice?.tts} />
        <div className="flex justify-end py-3 empty:hidden">
          <VoicePack />
        </div>
      </Section>

      <Section title="This PC">
        <Machine />
      </Section>

      <Section title="Advanced">
        <Row title="Always show the context meter" detail="How full the model's memory is, and exactly what is being sent.">
          <Switch label="Always show the context meter" checked={devTools} onChange={setDevTools} />
        </Row>
      </Section>
    </Sheet>
  );
}
