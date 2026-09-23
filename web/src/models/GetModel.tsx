// Getting a model, from inside the app. On first launch this opens by itself: the app ships the
// engine but no model, because models are gigabytes and which one fits depends on your graphics
// card. The list is the same ranking `make models` prints, best fit first.
import { AnimatePresence, motion } from "framer-motion";
import { Check, Download } from "lucide-react";
import type { ModelRecommendation } from "../api/types";
import Orb from "../brand/Orb";
import Sheet from "../shell/Sheet";
import { useDownloads } from "../store/downloads";
import { Button } from "../ui/controls";
import { GLIDE } from "../ui/motion";

const FIT: Record<string, string> = {
  fits: "Runs well on this PC",
  tight: "Fits, just",
  needs_offload: "Will run slowly on this PC",
  unavailable: "Couldn't check the fit",
};

const ACTIVE = ["resolving", "downloading", "verifying"];

function size(bytes: number | null | undefined): string {
  if (!bytes) return "";
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`;
}

function Progress() {
  const progress = useDownloads((s) => s.progress);
  const launch = useDownloads((s) => s.launch);
  const cancel = useDownloads((s) => s.cancel);
  if (!progress || progress.state === "idle") return null;
  const total = progress.bytes_total ?? 0;
  const fraction = total ? Math.min(1, progress.bytes_done / total) : 0;
  const busy = ACTIVE.includes(progress.state);
  const done = progress.state === "done";
  return (
    <div className="mb-5 rounded-3xl bg-accent/[0.07] p-5">
      <div className="flex items-center gap-3">
        <Orb size={32} state={busy ? "thinking" : "idle"} />
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-medium text-ink">
            {done ? `${progress.display_name} is ready` : `Getting ${progress.display_name}`}
          </p>
          <p className="text-[13px] text-ink-faint">
            {done
              ? launch?.detail ?? ""
              : `${size(progress.bytes_done) || "0 MB"} of ${size(total) || "…"}${progress.detail ? ` · ${progress.detail}` : ""}`}
          </p>
        </div>
        {busy && (
          <Button small tone="ghost" onClick={() => void cancel()}>
            Pause
          </Button>
        )}
      </div>
      {!done && (
        <div className="mt-4 h-2 overflow-hidden rounded-full bg-ink/[0.07]">
          <motion.div className="h-full rounded-full bg-accent" animate={{ width: `${fraction * 100}%` }} transition={GLIDE} />
        </div>
      )}
    </div>
  );
}

function Card({ rec, best }: { rec: ModelRecommendation; best: boolean }) {
  const start = useDownloads((s) => s.start);
  const busy = useDownloads((s) => ACTIVE.includes(s.progress?.state ?? ""));
  return (
    <div className={`flex items-start gap-4 rounded-3xl p-4 transition-colors ${best ? "bg-ink/[0.04]" : "hover:bg-ink/[0.03]"}`}>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-2 text-[15px] font-medium text-ink">
          {rec.display_name}
          {best && <span className="rounded-full bg-accent/12 px-2 py-0.5 text-[11.5px] font-medium text-accent">Best for this PC</span>}
        </p>
        <p className="mt-0.5 text-[12.5px] text-ink-faint">
          {FIT[rec.status] ?? FIT.unavailable}
          {rec.download_size_bytes ? ` · ${size(rec.download_size_bytes)}` : ""}
        </p>
        <p className="mt-1.5 text-[13.5px] leading-snug text-ink-muted">{rec.why}</p>
        {rec.note && <p className="mt-1 text-[12.5px] text-ink-faint">{rec.note}</p>}
      </div>
      {rec.installed ? (
        <span className="inline-flex h-8 items-center gap-1 text-[13px] text-success">
          <Check size={16} strokeWidth={2} /> Installed
        </span>
      ) : (
        <Button small tone={best ? "primary" : "secondary"} icon={Download} disabled={busy} onClick={() => void start(rec.key)}>
          Get
        </Button>
      )}
    </div>
  );
}

export default function GetModel() {
  const open = useDownloads((s) => s.open);
  const hide = useDownloads((s) => s.hide);
  const catalog = useDownloads((s) => s.catalog);
  const error = useDownloads((s) => s.error);
  const bestKey = catalog.find((r) => !r.installed && r.status === "fits")?.key ?? catalog[0]?.key;

  return (
    <AnimatePresence>
      {open && (
        <Sheet
          title="Choose a model"
          subtitle="The model is Jarvis's brain, and it runs entirely on this PC. These are ranked by what your graphics card can hold."
          onClose={hide}
          width={640}
        >
          <Progress />
          {error && <p className="mb-3 rounded-2xl bg-danger/[0.07] px-4 py-2.5 text-[13px] text-ink">{error}</p>}
          {catalog.length === 0 && <p className="shimmer py-6 text-center text-[14px] font-medium">Looking at this PC</p>}
          <div className="-mx-4">
            {catalog.map((rec) => (
              <Card key={rec.key} rec={rec} best={rec.key === bestKey} />
            ))}
          </div>
          <p className="mt-4 text-[12.5px] leading-relaxed text-ink-faint">
            Downloads come straight from each model's official page, are checked against their fingerprint, and pick up where they
            left off if the connection drops.
          </p>
        </Sheet>
      )}
    </AnimatePresence>
  );
}
