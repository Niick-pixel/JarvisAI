// Images: describe a picture and Jarvis paints it on this PC, and every picture you have made, newest
// first. Each one opens the chat it was made in, so you can ask for another take.
import { Palette } from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { GalleryItem } from "../api/types";
import Sheet from "../shell/Sheet";
import { useImages } from "../store/images";
import { useSession } from "../store/session";
import { useUi } from "../store/ui";
import { Button, FIELD, Segmented } from "../ui/controls";
import ImageSettings from "./ImageSettings";

export default function ImagesSheet() {
  const [items, setItems] = useState<GalleryItem[] | null>(null);
  const [prompt, setPrompt] = useState("");
  const ready = useImages((s) => s.status?.ready ?? false);
  const videoReady = useImages((s) => s.status?.video_ready ?? false);
  const [video, setVideo] = useState(false);
  useEffect(() => {
    void useImages.getState().refresh().catch(() => undefined);
    void request<GalleryItem[]>("/api/images/gallery").then(setItems).catch(() => setItems([]));
  }, []);

  const create = () => {
    const text = prompt.trim();
    if (!text) return;
    useUi.getState().closeSheet();
    useSession.getState().newChat();
    // Only the video model here: Create makes a clip.
    if (video || !ready) useImages.getState().setVideo(true);
    else useImages.getState().setMode(true);
    void useSession.getState().send(text);
  };
  const open = (id: string) => {
    useUi.getState().closeSheet();
    void useSession.getState().openConversation(id);
  };

  return (
    <Sheet title="Images" subtitle="Pictures made on this PC. Nothing you describe leaves it." width={900}>
      {(ready || videoReady) && (
        <form
          className="mb-6 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          {videoReady && ready && (
            <Segmented<"image" | "video">
              id="make"
              value={video ? "video" : "image"}
              onChange={(v) => setVideo(v === "video")}
              options={[
                { value: "image", label: "Image" },
                { value: "video", label: "Video" },
              ]}
            />
          )}
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={video || !ready ? "Describe a short video…" : "Describe an image…"}
            className={FIELD}
            autoFocus
          />
          <Button tone="primary" icon={Palette} disabled={!prompt.trim()} onClick={create}>
            Create
          </Button>
        </form>
      )}
      <details className="mb-6 rounded-3xl bg-ink/[0.03] px-4" open={!ready && !videoReady}>
        <summary className="cursor-pointer py-3 text-[13.5px] font-medium text-ink-muted">Models for pictures and video</summary>
        <ImageSettings />
      </details>
      {items === null ? (
        <p className="shimmer py-6 text-center text-[14px] font-medium">Loading your pictures</p>
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-[14px] text-ink-faint">No pictures yet. Describe one above.</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {items.map((item) => (
            <button
              key={item.attachment_id}
              type="button"
              onClick={() => open(item.conversation_id)}
              title={item.prompt}
              className="group overflow-hidden rounded-2xl bg-ink/[0.04] text-left"
            >
              {item.mime.startsWith("video/") ? (
                <video
                  src={`/api/attachments/${item.attachment_id}`}
                  muted
                  loop
                  playsInline
                  onMouseEnter={(e) => void e.currentTarget.play().catch(() => undefined)}
                  onMouseLeave={(e) => e.currentTarget.pause()}
                  className="aspect-square w-full object-cover"
                />
              ) : (
                <img src={`/api/attachments/${item.attachment_id}`} alt={item.prompt} loading="lazy" className="aspect-square w-full object-cover transition-transform group-hover:scale-[1.03]" />
              )}
              <p className="truncate px-2.5 py-2 text-[12.5px] text-ink-muted">{item.prompt || "Untitled"}</p>
            </button>
          ))}
        </div>
      )}
    </Sheet>
  );
}
