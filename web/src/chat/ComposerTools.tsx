// The left side of the composer: "+" for the bigger tools, and how hard to think.
import { BookOpen, Globe, Lightbulb, Plus, Users, X, Zap } from "lucide-react";
import { useSession } from "../store/session";
import { type ThinkMode, useUi } from "../store/ui";
import { IconButton } from "../ui/controls";
import Menu from "../ui/Menu";

const THINK: Record<ThinkMode, { label: string; detail: string }> = {
  auto: { label: "Auto", detail: "The model decides whether to think first" },
  on: { label: "Think", detail: "Reason step by step before answering. Slower, better at hard questions" },
  off: { label: "Fast", detail: "Answer straight away" },
};

function Chip({ label, icon: Icon, active, onClick, onClear }: {
  label: string;
  icon: typeof Globe;
  active?: boolean;
  onClick?: () => void;
  onClear?: () => void;
}) {
  return (
    <span
      className={`inline-flex h-9 items-center rounded-full text-[13.5px] font-medium transition-colors ${
        active ? "bg-accent/12 text-accent" : "text-ink-muted hover:bg-ink/[0.06] hover:text-ink"
      }`}
    >
      <button type="button" onClick={onClick} className="inline-flex h-full items-center gap-1.5 pl-3 pr-3">
        <Icon size={17} strokeWidth={1.75} />
        {label}
      </button>
      {onClear && (
        <button type="button" onClick={onClear} aria-label={`Turn off ${label}`} className="-ml-1.5 mr-1.5 rounded-full p-0.5 hover:bg-accent/15">
          <X size={14} strokeWidth={2} />
        </button>
      )}
    </span>
  );
}

export default function ComposerTools() {
  const research = useSession((s) => s.research);
  const setResearch = useSession((s) => s.setResearch);
  const think = useUi((s) => s.think);
  const setThink = useUi((s) => s.setThink);
  const openSheet = useUi((s) => s.openSheet);

  return (
    <div className="flex items-center gap-1">
      <Menu
        place="top-start"
        width={300}
        trigger={(open, toggle) => <IconButton icon={Plus} label="Tools" active={open} onClick={toggle} tip="top" />}
        items={[
          {
            key: "research",
            label: "Research the web",
            detail: "Search in rounds and cite what it finds",
            icon: Globe,
            checked: research,
            onSelect: () => setResearch(!research),
          },
          {
            key: "council",
            label: "Ask the council",
            detail: "Put one question to several models and compare",
            icon: Users,
            onSelect: () => openSheet("council"),
          },
          {
            key: "knowledge",
            label: "Add knowledge",
            detail: "Let Jarvis read a folder of your documents",
            icon: BookOpen,
            onSelect: () => openSheet("knowledge"),
          },
        ]}
      />
      <Menu
        place="top-start"
        width={300}
        trigger={(_, toggle) => (
          <Chip label={THINK[think].label} icon={think === "off" ? Zap : Lightbulb} active={think === "on"} onClick={toggle} />
        )}
        items={(Object.keys(THINK) as ThinkMode[]).map((mode) => ({
          key: mode,
          label: THINK[mode].label,
          detail: THINK[mode].detail,
          icon: mode === "off" ? Zap : Lightbulb,
          checked: think === mode,
          onSelect: () => setThink(mode),
        }))}
      />
      {research && <Chip label="Research" icon={Globe} active onClear={() => setResearch(false)} />}
    </div>
  );
}
