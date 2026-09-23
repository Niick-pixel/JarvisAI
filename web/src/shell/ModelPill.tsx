// The model switcher, at the top of the chat the way Gemini shows "2.5 Flash ⌄". Names are the
// friendly ones the server derives from the file; the arithmetic behind "fits" lives in Settings.
import { ChevronDown, Download, Sparkles } from "lucide-react";
import { useEffect } from "react";
import type { ModelOption } from "../api/types";
import { useDownloads } from "../store/downloads";
import { useLibrary } from "../store/library";
import Menu, { type MenuItem } from "../ui/Menu";

const FIT: Record<ModelOption["status"], string> = {
  fits: "Runs well on this PC",
  tight: "Fits, with little room to spare",
  needs_offload: "Will run slowly on this PC",
  unavailable: "Unknown fit",
};

function detail(option: ModelOption): string {
  const parts = [option.remote ? "Remote" : FIT[option.status]];
  if (option.model.quant) parts.push(option.model.quant);
  return parts.join(" · ");
}

export default function ModelPill() {
  const { models, selectedModelId, refreshModels, selectModel } = useLibrary();

  useEffect(() => {
    void refreshModels().catch(() => undefined);
  }, [refreshModels]);

  const auto = models.find((m) => m.recommended);
  const current = models.find((m) => m.model.id === selectedModelId) ?? auto;
  const label = current?.model.display_name ?? "No model";

  const items: MenuItem[] = [
    {
      key: "auto",
      label: "Automatic",
      detail: auto ? `Uses ${auto.model.display_name}, the best fit for this PC` : "Picks the best model this PC can run",
      icon: Sparkles,
      checked: !selectedModelId,
      onSelect: () => void selectModel(null),
    },
    ...models.map((option) => ({
      key: option.model.id,
      label: option.model.display_name,
      detail: detail(option),
      checked: option.model.id === selectedModelId,
      onSelect: () => void selectModel(option.model.id),
    })),
  ];

  return (
    <Menu
      width={320}
      items={items}
      footer={
        <>
          <div className="mx-3 my-1.5 h-px bg-ink/[0.06]" />
          <button
            type="button"
            onClick={() => void useDownloads.getState().show()}
            className="flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left text-[14px] text-ink-muted transition-colors hover:bg-ink/[0.05] hover:text-ink"
          >
            <Download size={18} strokeWidth={1.75} className="opacity-80" />
            Get more models
          </button>
        </>
      }
      trigger={(open, toggle) => (
        <button
          type="button"
          onClick={() => {
            if (!open) void refreshModels().catch(() => undefined);
            toggle();
          }}
          className="flex h-10 items-center gap-1.5 rounded-full px-3.5 text-[17px] text-ink transition-colors hover:bg-ink/[0.06]"
        >
          <span className="max-w-[16rem] truncate font-display font-medium tracking-tight">{label}</span>
          <ChevronDown size={17} strokeWidth={2} className={`text-ink-faint transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
      )}
    />
  );
}
