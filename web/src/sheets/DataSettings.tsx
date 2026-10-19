// Settings > Data & storage: what Jarvis keeps on this PC, how much room it takes, and a button to
// clear each kind - or everything. Every clear asks first; none of them can be undone.
import { Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { DataKind } from "../api/types";
import { toast } from "../store/toast";
import { Button, Row } from "../ui/controls";
import { useConfirm } from "../ui/confirm";
import { Group } from "./SettingsPanels";

type Kind = DataKind["kind"];

function size(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${Math.round(bytes / 1e6)} MB`;
  return bytes ? `${Math.max(1, Math.round(bytes / 1e3))} KB` : "empty";
}

const KINDS: {
  kind: Exclude<Kind, "everything">;
  title: string;
  detail: (d: DataKind) => string;
  warn: string;
}[] = [
  {
    kind: "chats",
    title: "Chats",
    detail: (d) =>
      `${d.count} chats · ${size(d.bytes)} of attachments and pictures`,
    warn: "Every chat, with its attachments and generated pictures, will be deleted.",
  },
  {
    kind: "memory",
    title: "Memory",
    detail: (d) =>
      d.count
        ? `${d.count} things Jarvis remembers about you`
        : "Nothing remembered yet",
    warn: "Jarvis will forget everything it has learned about you.",
  },
  {
    kind: "knowledge",
    title: "Knowledge index",
    detail: (d) =>
      `${d.count} folders indexed. Your files themselves are never touched.`,
    warn: "The search index of your folders will be removed. Your files stay where they are.",
  },
  {
    kind: "cache",
    title: "Cache",
    detail: (d) =>
      d.bytes
        ? `${size(d.bytes)} of downloaded updates, backups and logs`
        : "Nothing cached",
    warn: "Downloaded updates, file backups and logs will be removed.",
  },
  {
    kind: "models",
    title: "Downloaded models",
    detail: (d) =>
      d.count ? `${d.count} files · ${size(d.bytes)}` : "No models downloaded",
    warn: "All downloaded chat and image models will be deleted. Getting them back means downloading them again.",
  },
];

export default function DataSettings() {
  const [usage, setUsage] = useState<DataKind[]>([]);
  const load = () =>
    void request<DataKind[]>("/api/data")
      .then(setUsage)
      .catch(() => undefined);
  useEffect(load, []);

  const clear = async (kind: Kind, title: string, warn: string) => {
    const yes = await useConfirm.getState().ask({
      title: `Clear ${title.toLowerCase()}?`,
      body: `${warn} This cannot be undone.`,
      confirm: "Clear",
      danger: true,
    });
    if (!yes) return;
    try {
      setUsage(
        await request<DataKind[]>("/api/data/clear", {
          method: "POST",
          body: JSON.stringify({ kind }),
        }),
      );
      toast(`${title} cleared.`);
      if (kind === "everything") {
        try {
          localStorage.clear();
        } catch {
          // Storage may be unavailable; the server side is already clear.
        }
        window.location.reload();
      }
    } catch {
      toast(`Couldn't clear ${title.toLowerCase()}.`, "error");
    }
  };

  const by = Object.fromEntries(usage.map((d) => [d.kind, d]));
  return (
    <>
      <Group title="Stored on this PC">
        {KINDS.map(({ kind, title, detail, warn }) => (
          <Row
            key={kind}
            title={title}
            detail={by[kind] ? detail(by[kind]) : "Checking…"}
          >
            <Button
              small
              tone="ghost"
              icon={Trash2}
              onClick={() => void clear(kind, title, warn)}
            >
              Clear
            </Button>
          </Row>
        ))}
      </Group>
      <Group title="Start over">
        <Row
          title="Reset Jarvis"
          detail="Chats, memory, knowledge, workflows, connections and settings - back to a fresh install. Downloaded models are kept."
        >
          <Button
            small
            tone="danger"
            onClick={() =>
              void clear(
                "everything",
                "Everything",
                "Jarvis will be reset to a fresh install: chats, memory, knowledge, workflows, connections and settings. Downloaded models are kept.",
              )
            }
          >
            Reset
          </Button>
        </Row>
      </Group>
    </>
  );
}
