// Settings > Voice: the natural voice. Kokoro sounds like a person reading rather than a machine;
// it is a one-time download (about 120 MB) and runs on this PC. Each voice can be heard before
// it is chosen, and Piper stays one switch away.
import { Check, Download, Play, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "../api/client";
import type { KokoroStatus } from "../api/types";
import { toast } from "../store/toast";
import { Button, Row, Switch } from "../ui/controls";

const put = (body: { engine?: "kokoro" | "piper"; voice?: string }) =>
  request<KokoroStatus>("/api/voice/kokoro", { method: "PUT", body: JSON.stringify(body) });

function mb(bytes: number): string {
  return `${Math.round(bytes / 1e6)} MB`;
}

export default function KokoroSettings() {
  const [status, setStatus] = useState<KokoroStatus | null>(null);
  const [playing, setPlaying] = useState<string | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const load = () => request<KokoroStatus>("/api/voice/kokoro").then(setStatus);

  useEffect(() => {
    void load().catch(() => undefined);
    return () => audio.current?.pause();
  }, []);
  const downloading = status?.download.state === "downloading" || status?.download.state === "verifying";
  useEffect(() => {
    if (!downloading) return;
    const timer = window.setInterval(() => void load().catch(() => undefined), 1000);
    return () => window.clearInterval(timer);
  }, [downloading]);

  if (!status) return <Row title="Natural voice" detail="Checking…" />;
  if (!status.in_this_build) return null;

  const preview = (voice: string) => {
    audio.current?.pause();
    if (playing === voice) return setPlaying(null);
    const player = new Audio(`/api/voice/kokoro/preview?voice=${voice}`);
    player.onended = () => setPlaying(null);
    player.onerror = () => setPlaying(null);
    audio.current = player;
    setPlaying(voice);
    void player.play().catch(() => setPlaying(null));
  };
  const choose = async (body: Parameters<typeof put>[0]) => {
    try {
      setStatus(await put(body));
    } catch (error) {
      toast(error instanceof ApiError ? error.body.message : "Couldn't change the voice", "error");
    }
  };

  if (!status.installed) {
    const d = status.download;
    return (
      <Row
        title="Natural voice"
        detail={
          downloading
            ? `Getting it… ${mb(d.bytes_done)} of ${mb(d.bytes_total)}`
            : d.state === "failed"
              ? d.detail
              : "Kokoro sounds like a person, not a machine reading. About 120 MB, once; it runs on this PC."
        }
      >
        <Button small icon={Download} disabled={downloading} onClick={() => void request<KokoroStatus>("/api/voice/kokoro/download", { method: "POST" }).then(setStatus)}>
          {downloading ? "Getting…" : "Get"}
        </Button>
      </Row>
    );
  }

  const on = status.engine === "kokoro";
  return (
    <>
      <Row title="Natural voice" detail={on ? "Kokoro speaks for Jarvis everywhere: voice mode, read aloud, briefings and alerts." : "Off - the simpler Piper voice is speaking."}>
        <Switch label="Natural voice" checked={on} onChange={(v) => void choose({ engine: v ? "kokoro" : "piper" })} />
      </Row>
      {on &&
        status.voices.map(([id, description]) => {
          const [name, ...rest] = (description ?? "").split(" - ");
          const chosen = id === status.voice;
          return (
            <div key={id} className="flex items-center gap-3 py-2.5">
              <button type="button" onClick={() => id && preview(id)} aria-label={`Hear ${name}`} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink/[0.05] text-ink-muted hover:bg-ink/10 hover:text-ink">
                {playing === id ? <Square size={14} /> : <Play size={14} />}
              </button>
              <button type="button" onClick={() => id && void choose({ voice: id })} className="min-w-0 flex-1 text-left">
                <span className="block text-[14px] font-medium text-ink">{name}</span>
                <span className="block text-[12.5px] text-ink-faint">{rest.join(" - ")}</span>
              </button>
              {chosen && <Check size={18} className="text-accent" />}
            </div>
          );
        })}
    </>
  );
}
