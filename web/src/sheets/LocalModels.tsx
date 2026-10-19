// Settings > Models: the model files on this PC - how big, which one is serving - with Use to switch
// the engine to one and Delete to get the disk space back.
import { Download, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { LocalModel, LocalModels as Library } from "../api/types";
import { useDownloads } from "../store/downloads";
import { useLibrary } from "../store/library";
import { toast } from "../store/toast";
import { Button, IconButton, Row } from "../ui/controls";

const gb = (bytes: number) => (bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`);
const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

export default function LocalModels() {
  const [library, setLibrary] = useState<Library | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => void request<Library>("/api/models/local").then(setLibrary).catch(() => undefined);
  useEffect(load, []);

  const act = async (model: LocalModel, verb: "use" | "delete") => {
    if (verb === "delete" && !window.confirm(`Delete ${model.display_name}? This removes ${gb(model.size_bytes)} from this PC.`)) return;
    setBusy(model.id);
    try {
      const path = `/api/models/local/${encodeURIComponent(model.id)}`;
      setLibrary(await request<Library>(verb === "use" ? `${path}/use` : path, { method: verb === "use" ? "POST" : "DELETE" }));
      toast(verb === "use" ? `Switched to ${model.display_name}.` : `Deleted ${model.display_name}.`);
      void useLibrary.getState().refreshModels().catch(() => undefined);
    } catch (error) {
      toast(message(error), "error");
    }
    setBusy(null);
  };

  if (!library) return <Row title="Models on this PC" detail="Looking…" />;
  return (
    <>
      {library.models.length === 0 && <Row title="No models yet" detail="Download one to start chatting." />}
      {library.models.map((model) => (
        <Row
          key={model.id}
          title={model.display_name}
          detail={[
            model.quant,
            gb(model.size_bytes),
            model.loaded ? "In use now" : "",
            model.pinned && !model.loaded ? "Chosen" : "",
          ]
            .filter(Boolean)
            .join(" · ")}
        >
          <div className="flex shrink-0 items-center gap-1">
            {!model.loaded && (
              <Button small tone="ghost" disabled={busy !== null} onClick={() => void act(model, "use")}>
                {busy === model.id ? "Switching…" : "Use"}
              </Button>
            )}
            {model.deletable && (
              <IconButton icon={Trash2} label="Delete" size={32} onClick={() => busy === null && void act(model, "delete")} />
            )}
          </div>
        </Row>
      ))}
      <Row title={`${gb(library.total_bytes)} in ${library.folder}`}>
        <Button small icon={Download} onClick={() => void useDownloads.getState().show()}>
          Get more
        </Button>
      </Row>
    </>
  );
}
