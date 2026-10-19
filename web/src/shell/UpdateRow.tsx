// The one place an update shows outside Settings: a quiet row above Home once the new version is
// downloaded and verified, styled like the rows around it. Before that, updating happens in the
// background (or from Settings > Updates) and asks for nothing.
import { RotateCw } from "lucide-react";
import { useEffect } from "react";
import { useUpdates, watchUpdates } from "../store/updates";

export default function UpdateRow({ open }: { open: boolean }) {
  const status = useUpdates((s) => s.status);
  const updateNow = useUpdates((s) => s.updateNow);
  useEffect(() => watchUpdates(), []);

  if (status?.state !== "ready" && status?.state !== "installing") return null;
  const installing = status.state === "installing";
  const label = installing ? "Restarting…" : `Restart for ${status.latest}`;
  return (
    <button
      type="button"
      disabled={installing}
      onClick={() => void updateNow()}
      aria-label={label}
      title={open ? undefined : label}
      className="relative flex h-10 w-full items-center gap-3 rounded-full px-3 text-[14px] text-ink-muted transition-colors hover:bg-ink/[0.06] hover:text-ink"
    >
      <span className="relative shrink-0">
        <RotateCw size={19} strokeWidth={1.75} />
        <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-accent" />
      </span>
      {open && <span className="truncate">{label}</span>}
    </button>
  );
}
