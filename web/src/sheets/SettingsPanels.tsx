// The pages of Settings. Each is a plain list of rows under a heading or two; SettingsSheet puts
// them behind the menu on the left.
import { Download, Monitor, Moon, Sun } from "lucide-react";
import type { ReactNode } from "react";
import type { EngineStatus } from "../api/types";
import { type ThemeMode, useAppearance } from "../design/theme";
import { useDownloads } from "../store/downloads";
import { useLibrary } from "../store/library";
import { type ThinkMode, useUi } from "../store/ui";
import { useVoice } from "../store/voice";
import { Button, FIELD, Row, Segmented, Switch } from "../ui/controls";
import VoicePack from "../voice/VoicePack";
import LocalModels from "./LocalModels";
import WakeRow from "./WakeRow";

export function Group({
  title,
  children,
}: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-8 last:mb-2">
      {title && (
        <h3 className="mb-1 text-[15px] font-semibold text-ink">{title}</h3>
      )}
      <div className="divide-y divide-ink/[0.06]">{children}</div>
    </section>
  );
}

function Engine({ title, engine }: { title: string; engine?: EngineStatus }) {
  if (!engine) return <Row title={title} detail="Checking…" />;
  if (engine.available) {
    return (
      <Row
        title={title}
        detail={`Ready - runs on this PC (${engine.engine}, ${engine.device})`}
      />
    );
  }
  const fix = engine.fix && !engine.downloadable ? ` ${engine.fix}` : "";
  return <Row title={title} detail={`${engine.reason}${fix}`} />;
}

export function General() {
  const { mode, setMode, reduceEffects, setReduceEffects } = useAppearance();
  const { name, setName } = useUi();
  return (
    <>
      <Group title="Profile">
        <Row
          title="What should Jarvis call you?"
          detail="Used in the greeting and when it talks to you."
        >
          <div className="w-56 shrink-0">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className={FIELD}
            />
          </div>
        </Row>
      </Group>
      <Group title="Appearance">
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
        <Row
          title="Reduce effects"
          detail="Keep the glow still. Also gives a little more of the GPU back to the model."
        >
          <Switch
            label="Reduce effects"
            checked={reduceEffects}
            onChange={setReduceEffects}
          />
        </Row>
      </Group>
    </>
  );
}

export function Answers() {
  const { think, setThink } = useUi();
  const { models, selectedModelId } = useLibrary();
  const current =
    models.find((m) => m.model.id === selectedModelId) ??
    models.find((m) => m.recommended);
  return (
    <>
      <Group title="Thinking">
        <Row
          title="How long to think"
          detail="How long reasoning models think before they answer. Heavy makes them keep checking their work, much longer. You can change it per message too."
        >
          <Segmented<ThinkMode>
            id="think"
            value={think}
            onChange={setThink}
            options={[
              { value: "off", label: "Fast" },
              { value: "auto", label: "Auto" },
              { value: "on", label: "Think" },
              { value: "heavy", label: "Heavy" },
            ]}
          />
        </Row>
      </Group>
      <Group title="Model">
        <Row
          title={current ? current.model.display_name : "No model yet"}
          detail={
            current?.budget?.explanation ??
            current?.reason ??
            "Download one to get started."
          }
        >
          <Button
            small
            icon={Download}
            onClick={() => void useDownloads.getState().show()}
          >
            Get models
          </Button>
        </Row>
      </Group>
      <Group title="On this PC">
        <LocalModels />
      </Group>
    </>
  );
}

export function Voice() {
  const voice = useVoice((s) => s.status);
  return (
    <Group title="Voice">
      <Engine title="Dictation" engine={voice?.stt} />
      <Engine title="Reading aloud" engine={voice?.tts} />
      <WakeRow />
      <div className="flex justify-end py-3 empty:hidden">
        <VoicePack />
      </div>
    </Group>
  );
}

export function Developer() {
  const { devTools, setDevTools } = useUi();
  return (
    <Group title="Developer">
      <Row
        title="Always show the context meter"
        detail="How full the model's memory is, and exactly what is being sent."
      >
        <Switch
          label="Always show the context meter"
          checked={devTools}
          onChange={setDevTools}
        />
      </Row>
    </Group>
  );
}
