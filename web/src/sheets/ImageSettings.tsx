// The models that make pictures and video on this PC, with stable-diffusion.cpp. Nothing is fetched
// until you choose one; the engine (about 50 MB) comes with the first. The big ones say how big,
// and ask before a download that size.
import { Download } from "lucide-react";
import { useEffect } from "react";
import type { ImageStatus } from "../api/types";
import { useImages } from "../store/images";
import { Button, Row } from "../ui/controls";
import { useConfirm } from "../ui/confirm";

type Option = ImageStatus["options"][number];

async function get(option: Option, install: (key: string) => Promise<void>) {
  if (option.heavy || option.size_gb >= 5) {
    const yes = await useConfirm.getState().ask({
      title: `${option.display_name} is a big download`,
      body: `${option.why} About ${option.size_gb.toFixed(0)} GB in all, resumable if it stops. While it ${
        option.video ? "makes a clip" : "paints"
      }, the graphics card is fully busy, so the chat model answers slowly.`,
      confirm: "Download",
      danger: option.heavy,
    });
    if (!yes) return;
  }
  await install(option.key);
}

function Badge({ option }: { option: Option }) {
  const label = option.video ? "Experimental" : option.heavy ? "Heavy" : "";
  return label ? <span className="ml-2 rounded-full bg-accent/12 px-2 py-0.5 text-[11px] font-medium text-accent">{label}</span> : null;
}

export default function ImageSettings() {
  const { status, refresh, install } = useImages();
  useEffect(() => void refresh().catch(() => undefined), [refresh]);
  if (!status) return <Row title="Making pictures" detail="Checking…" />;
  const installing = status.state === "installing";
  return (
    <>
      <Row
        title="Making pictures and video"
        detail={
          installing
            ? status.detail || "Downloading…"
            : status.state === "failed"
              ? status.detail
              : status.ready
                ? `Ready - "Create an image" in the + menu, or Images in the sidebar. ${status.detail}`.trim()
                : "Pick a model to download. It runs on this PC with stable-diffusion.cpp."
        }
      />
      {status.options.map((option) => (
        <Row
          key={option.key}
          title={option.display_name}
          detail={`${option.why}${option.size_gb ? ` · ${option.size_gb.toFixed(1)} GB` : ""} · ${option.license}.`}
        >
          <Badge option={option} />
          {option.installed ? (
            option.video || option.key === status.model ? (
              <span className="shrink-0 text-[12.5px] text-ink-faint">{option.video ? "Ready" : "In use"}</span>
            ) : (
              <Button small tone="ghost" disabled={installing} onClick={() => void install(option.key)}>
                Use
              </Button>
            )
          ) : (
            <Button small icon={Download} disabled={installing} onClick={() => void get(option, install)}>
              Get
            </Button>
          )}
        </Row>
      ))}
    </>
  );
}
