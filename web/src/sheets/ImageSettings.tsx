// Settings > Images: making pictures on this PC with stable-diffusion.cpp. Nothing is fetched until
// you choose a model; the engine (about 50 MB) comes with the first one.
import { Download } from "lucide-react";
import { useEffect } from "react";
import { useImages } from "../store/images";
import { Button, Row } from "../ui/controls";

export default function ImageSettings() {
  const { status, refresh, install } = useImages();
  useEffect(() => void refresh().catch(() => undefined), [refresh]);
  if (!status) return <Row title="Making pictures" detail="Checking…" />;
  const installing = status.state === "installing";
  return (
    <>
      <Row
        title="Making pictures"
        detail={
          status.ready
            ? `Ready - "Create an image" in the + menu. ${status.detail}`.trim()
            : installing
              ? status.detail || "Downloading…"
              : status.state === "failed"
                ? status.detail
                : "Pick a model to download. It runs on this PC with stable-diffusion.cpp."
        }
      />
      {status.options.map((option) => (
        <Row key={option.key} title={option.display_name} detail={`${option.why} ${option.license}.`}>
          {option.installed ? (
            <span className="text-[12.5px] text-ink-faint">{option.key === status.model ? "In use" : "Downloaded"}</span>
          ) : (
            <Button small icon={Download} disabled={installing} onClick={() => void install(option.key)}>
              Get
            </Button>
          )}
        </Row>
      ))}
    </>
  );
}
