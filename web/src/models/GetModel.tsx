// Getting a model, from inside the app. On first launch this opens by itself: the desktop app
// ships llama.cpp but no weights, because weights are gigabytes and which ones fit is a question
// about your card, not ours. The list is the same ranking `make models` prints.
import { AnimatePresence, motion } from "framer-motion";
import type { ModelRecommendation } from "../api/types";
import { useDownloads } from "../store/downloads";
import Button from "../ui/Button";
import { SPRING } from "../ui/motion";

const BADGE: Record<string, { label: string; className: string }> = {
  fits: { label: "fits", className: "bg-emerald-400/15 text-emerald-200" },
  tight: { label: "tight", className: "bg-amber-400/15 text-amber-200" },
  needs_offload: { label: "too big for the card", className: "bg-rose-400/15 text-rose-200" },
  unavailable: { label: "unknown", className: "bg-white/10 text-ink-faint" },
};

function gb(bytes: number | null | undefined): string {
  if (!bytes) return "size unknown";
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(1)} GB` : `${Math.round(bytes / 1e6)} MB`;
}

function Progress() {
  const progress = useDownloads((s) => s.progress);
  const launch = useDownloads((s) => s.launch);
  const cancel = useDownloads((s) => s.cancel);
  if (!progress || progress.state === "idle") return null;
  const total = progress.bytes_total ?? 0;
  const fraction = total ? Math.min(1, progress.bytes_done / total) : 0;
  const busy = ["resolving", "downloading", "verifying"].includes(progress.state);
  return (
    <div className="glass mb-3 rounded-xl p-3 text-sm">
      <div className="flex items-baseline gap-2">
        <span className="text-ink">{progress.display_name}</span>
        <span className="text-ink-faint">{progress.state}</span>
        {busy && (
          <span className="ml-auto">
            <Button onClick={() => void cancel()}>Pause</Button>
          </span>
        )}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className="h-full rounded-full bg-sky-300/80"
          style={{ transform: `scaleX(${fraction})`, transformOrigin: "left" }}
        />
      </div>
      <p className="mt-1.5 text-[11px] text-ink-faint">
        {gb(progress.bytes_done)} of {gb(total)}
        {progress.resumed_from > 0 && ` · resumed from ${gb(progress.resumed_from)}`}
        {progress.detail && ` · ${progress.detail}`}
      </p>
      {progress.state === "done" && launch && (
        <p className="mt-1 text-[11px] text-ink-muted">
          {launch.started ? `Ready: ${launch.detail}` : launch.detail}
        </p>
      )}
    </div>
  );
}

function Row({ rec }: { rec: ModelRecommendation }) {
  const start = useDownloads((s) => s.start);
  const busy = useDownloads((s) =>
    ["resolving", "downloading", "verifying"].includes(s.progress?.state ?? ""),
  );
  const badge = BADGE[rec.status] ?? BADGE.unavailable!;
  return (
    <div className="rounded-xl border border-transparent px-3 py-2.5 hover:bg-white/6">
      <div className="flex items-center gap-2">
        <span className="text-sm text-ink">{rec.display_name}</span>
        <span className={`rounded-full px-1.5 py-0.5 text-[10px] ${badge.className}`}>
          {badge.label}
        </span>
        <span className="text-[11px] text-ink-faint">{gb(rec.download_size_bytes)}</span>
        <span className="ml-auto">
          {rec.installed ? (
            <span className="text-[11px] text-emerald-200">on this machine</span>
          ) : (
            <Button variant="primary" disabled={busy} onClick={() => void start(rec.key)}>
              Download
            </Button>
          )}
        </span>
      </div>
      <p className="mt-1 text-[11px] leading-snug text-ink-faint">{rec.why}</p>
      {rec.note && <p className="mt-0.5 text-[11px] text-ink-faint">{rec.note}</p>}
    </div>
  );
}

export default function GetModel() {
  const open = useDownloads((s) => s.open);
  const hide = useDownloads((s) => s.hide);
  const catalog = useDownloads((s) => s.catalog);
  const error = useDownloads((s) => s.error);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-6"
        >
          <motion.div
            initial={{ y: 12, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            transition={SPRING}
            className="scrim max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-white/10 p-5"
          >
            <div className="mb-1 flex items-center">
              <h2 className="text-lg text-ink">Pick a model for this machine</h2>
              <span className="ml-auto">
                <Button onClick={hide}>Close</Button>
              </span>
            </div>
            <p className="mb-4 text-sm text-ink-muted">
              Ranked by what your card can actually hold, next to the browser that shares it.
              Downloads come straight from the model&apos;s published repository, are checked
              against its hash, and resume if the connection drops.
            </p>
            <Progress />
            {error && <p className="mb-3 text-sm text-rose-200">{error}</p>}
            {catalog.length === 0 && (
              <p className="text-sm text-ink-faint">Reading the catalogue and this machine…</p>
            )}
            {catalog.map((rec) => (
              <Row key={rec.key} rec={rec} />
            ))}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
