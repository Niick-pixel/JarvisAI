// Settings, laid out like a desktop app's: a menu of pages on the left, in groups - you and how
// Jarvis answers, what it connects to, this computer - and one page at a time on the right.
// On a phone the menu becomes a row of chips above the page.
import type { LucideIcon } from "lucide-react";
import {
  AtSign,
  Code2,
  Database,
  Image,
  Mic,
  MonitorSmartphone,
  RefreshCw,
  Search,
  Settings2,
  Smartphone,
  Sparkles,
  Sun,
} from "lucide-react";
import { type ReactNode, useState } from "react";
import Sheet from "../shell/Sheet";
import { FIELD } from "../ui/controls";
import AccountsSettings from "./AccountsSettings";
import BriefingSettings from "./BriefingSettings";
import DataSettings from "./DataSettings";
import ImageSettings from "./ImageSettings";
import Machine from "./Machine";
import PhoneSettings from "./PhoneSettings";
import { Answers, Developer, General, Group, Voice } from "./SettingsPanels";
import Updates from "./Updates";

interface Page {
  id: string;
  label: string;
  icon: LucideIcon;
  /** Extra words the search box matches, beyond the label. */
  keywords: string;
  render: () => ReactNode;
}

const GROUPS: { title: string; pages: Page[] }[] = [
  {
    title: "Settings",
    pages: [
      {
        id: "general",
        label: "General",
        icon: Settings2,
        keywords: "name profile theme dark light effects glow",
        render: () => <General />,
      },
      {
        id: "answers",
        label: "Models & answers",
        icon: Sparkles,
        keywords: "model thinking reasoning download delete",
        render: () => <Answers />,
      },
      {
        id: "voice",
        label: "Voice",
        icon: Mic,
        keywords: "dictation speech wake word hey jarvis read aloud",
        render: () => <Voice />,
      },
      {
        id: "briefing",
        label: "Morning briefing",
        icon: Sun,
        keywords: "briefing schedule morning",
        render: () => (
          <Group title="Every morning">
            <BriefingSettings />
          </Group>
        ),
      },
      {
        id: "images",
        label: "Images",
        icon: Image,
        keywords: "picture generate stable diffusion",
        render: () => (
          <Group title="Making pictures">
            <ImageSettings />
          </Group>
        ),
      },
    ],
  },
  {
    title: "Connections",
    pages: [
      {
        id: "accounts",
        label: "Accounts",
        icon: AtSign,
        keywords: "gmail email mail github token connect home assistant",
        render: () => <AccountsSettings />,
      },
      {
        id: "phone",
        label: "Phone",
        icon: Smartphone,
        keywords: "phone pair qr mobile",
        render: () => (
          <Group title="Phone">
            <PhoneSettings />
          </Group>
        ),
      },
    ],
  },
  {
    title: "This computer",
    pages: [
      {
        id: "system",
        label: "System",
        icon: MonitorSmartphone,
        keywords: "gpu vram ram hardware",
        render: () => (
          <Group title="This PC">
            <Machine />
          </Group>
        ),
      },
      {
        id: "updates",
        label: "Updates",
        icon: RefreshCw,
        keywords: "version update upgrade",
        render: () => (
          <Group title="Updates">
            <Updates />
          </Group>
        ),
      },
      {
        id: "data",
        label: "Data & storage",
        icon: Database,
        keywords: "clear delete reset cache memory chats storage",
        render: () => <DataSettings />,
      },
      {
        id: "developer",
        label: "Developer",
        icon: Code2,
        keywords: "context meter advanced",
        render: () => <Developer />,
      },
    ],
  },
];

const ALL = GROUPS.flatMap((g) => g.pages);
let remembered = "general";

function NavItem({
  page,
  active,
  onClick,
}: {
  page: Page;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = page.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`flex shrink-0 items-center gap-3 rounded-xl px-3 py-2 text-left text-[14px] transition-colors ${
        active
          ? "bg-ink/[0.07] font-medium text-ink"
          : "text-ink-muted hover:bg-ink/[0.04] hover:text-ink"
      }`}
    >
      <Icon size={17} strokeWidth={1.6} className="shrink-0" />
      <span className="whitespace-nowrap">{page.label}</span>
    </button>
  );
}

export default function SettingsSheet() {
  const [current, setCurrent] = useState(remembered);
  const [query, setQuery] = useState("");
  const open = (id: string) => {
    remembered = id;
    setCurrent(id);
  };
  const q = query.trim().toLowerCase();
  const visible = (p: Page) =>
    !q || `${p.label} ${p.keywords}`.toLowerCase().includes(q);
  const page = ALL.find((p) => p.id === current) ?? (ALL[0] as Page);

  return (
    <Sheet title="Settings" width={960} bare>
      <div className="flex min-h-0 flex-1 flex-col sm:flex-row">
        <nav className="scroll-quiet flex shrink-0 gap-1 overflow-x-auto border-ink/[0.06] px-3 pb-3 sm:w-60 sm:flex-col sm:overflow-y-auto sm:border-r sm:px-4 sm:pb-6">
          <div className="relative mb-2 hidden sm:block">
            <Search
              size={15}
              strokeWidth={1.6}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint"
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search"
              className={`${FIELD} !py-2 pl-9 !text-[13.5px]`}
            />
          </div>
          {GROUPS.map((group) => {
            const pages = group.pages.filter(visible);
            if (!pages.length) return null;
            return (
              <div key={group.title} className="flex gap-1 sm:mb-3 sm:flex-col">
                <p className="hidden px-3 pb-1 pt-2 text-[12px] font-medium text-ink-faint sm:block">
                  {group.title}
                </p>
                {pages.map((p) => (
                  <NavItem
                    key={p.id}
                    page={p}
                    active={p.id === page.id}
                    onClick={() => open(p.id)}
                  />
                ))}
              </div>
            );
          })}
        </nav>
        <div
          key={page.id}
          className="scroll-quiet min-h-0 flex-1 overflow-y-auto px-4 pb-8 pt-1 sm:px-8"
        >
          {page.render()}
        </div>
      </div>
    </Sheet>
  );
}
