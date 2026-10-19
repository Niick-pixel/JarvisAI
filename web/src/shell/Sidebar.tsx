// The left rail, after Gemini: new chat and search at the top, your chats grouped by when, and the
// places that are not chats - Memory, Knowledge, Agents, Settings - as quiet rows at the bottom.
// Collapses to a strip of icons; nothing in it ever opens beside something else.
import { AnimatePresence, motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Bot, Brain, CandlestickChart, Download, Ellipsis, FolderCode, House, Library, PanelLeft, Search, Settings, SquarePen, Trash2, Image as ImageIcon, SquareTerminal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Conversation } from "../api/types";
import Orb from "../brand/Orb";
import { useAgents } from "../store/agents";
import { useLibrary } from "../store/library";
import { useSession } from "../store/session";
import { toast } from "../store/toast";
import { type SheetName, useUi } from "../store/ui";
import { IconButton, Tip } from "../ui/controls";
import Menu from "../ui/Menu";
import { GLIDE } from "../ui/motion";
import { useNarrow } from "../ui/narrow";
import UpdateRow from "./UpdateRow";
import { useCode } from "../store/code";

function bucket(ms: number): string {
  const days = Math.floor((Date.now() - ms) / 86_400_000);
  if (days < 1) return "Today";
  if (days < 2) return "Yesterday";
  if (days < 7) return "Previous 7 days";
  if (days < 30) return "Previous 30 days";
  return "Older";
}

function NavRow({
  icon: Icon,
  label,
  open,
  active,
  badge,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  open: boolean;
  active?: boolean;
  badge?: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={`group/tip relative flex h-10 w-full items-center gap-3 rounded-full px-3 text-[14px] transition-colors ${
        active ? "bg-accent/12 text-accent" : "text-ink-muted hover:bg-ink/[0.06] hover:text-ink"
      }`}
    >
      <span className="relative shrink-0">
        <Icon size={19} strokeWidth={1.75} />
        {!!badge && (
          <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-on-accent">
            {badge}
          </span>
        )}
      </span>
      {open ? <span className="truncate">{label}</span> : <Tip side="right">{label}</Tip>}
    </button>
  );
}

function ChatRow({ conversation, active }: { conversation: Conversation; active: boolean }) {
  const open = useLibrary((s) => s.open);
  const remove = useLibrary((s) => s.remove);
  const running = useSession((s) => s.runId) !== null;
  return (
    <div
      className={`group relative flex h-9 items-center rounded-full pl-3 pr-1 transition-colors ${
        active ? "bg-accent/12 text-ink" : "text-ink-muted hover:bg-ink/[0.05] hover:text-ink"
      }`}
    >
      <button
        type="button"
        onClick={() => void open(conversation.id)}
        disabled={running}
        className="min-w-0 flex-1 truncate text-left text-[14px] disabled:opacity-60"
        title={running ? "Stop the answer in progress first" : conversation.title || "New chat"}
      >
        {conversation.title || "New chat"}
      </button>
      <div className="opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
        <Menu
          place="bottom-end"
          width={230}
          trigger={(_, toggle) => <IconButton icon={Ellipsis} label="More" size={28} tip="none" onClick={toggle} />}
          items={[
            {
              key: "export",
              label: "Export to vault",
              detail: "Markdown with front-matter, into your notes folder",
              icon: Download,
              onSelect: () =>
                void api
                  .exportConversation(conversation.id)
                  .then((r) => toast(`Saved to ${r.path}`))
                  .catch(() => toast("Couldn't export - check the vault folder in Settings", "error")),
            },
            {
              key: "delete",
              label: "Delete",
              icon: Trash2,
              danger: true,
              onSelect: () => void remove(conversation.id),
            },
          ]}
        />
      </div>
    </div>
  );
}

export default function Sidebar() {
  const open = useUi((s) => s.sidebarOpen);
  const toggle = useUi((s) => s.toggleSidebar);
  const sheet = useUi((s) => s.sheet);
  const codeOn = useCode((s) => s.on);
  const openSheet = useUi((s) => s.openSheet);
  const { conversations, refresh } = useLibrary();
  const newChat = useSession((s) => s.newChat);
  const activeId = useSession((s) => s.conversation?.id);
  const waiting = useAgents((s) => s.pending.length);
  const [query, setQuery] = useState<string | null>(null);

  useEffect(() => {
    void refresh().catch(() => undefined);
  }, [refresh]);

  const groups = useMemo(() => {
    const needle = query?.trim().toLowerCase() ?? "";
    const out = new Map<string, Conversation[]>();
    for (const c of conversations) {
      if (needle && !(c.title || "").toLowerCase().includes(needle)) continue;
      const key = bucket(c.updated_at);
      out.set(key, [...(out.get(key) ?? []), c]);
    }
    return [...out.entries()];
  }, [conversations, query]);

  const place = (name: SheetName) => () => openSheet(name);
  const narrow = useNarrow();
  const drawer = useUi((s) => s.drawer);
  const setDrawer = useUi((s) => s.setDrawer);
  // On a phone the drawer gets out of the way as soon as you have picked something.
  useEffect(() => {
    if (narrow) setDrawer(false);
  }, [narrow, sheet, activeId, setDrawer]);
  if (narrow && !drawer) return null;
  const wide = narrow || open;

  return (
    <>
    {narrow && <div className="fixed inset-0 z-40 bg-bg/60 backdrop-blur-sm" onClick={() => setDrawer(false)} />}
    <motion.aside
      initial={narrow ? { x: -280 } : false}
      animate={narrow ? { x: 0, width: 272 } : { width: open ? 272 : 68 }}
      transition={GLIDE}
      className={`flex h-full shrink-0 flex-col overflow-hidden bg-sidebar px-2.5 pb-3 pt-3 ${
        narrow ? "fixed left-0 top-0 z-50 shadow-float" : "relative z-20"
      }`}
    >
      <div className="flex h-10 items-center gap-2 pl-0.5">
        <IconButton
          icon={PanelLeft}
          label={narrow ? "Close" : open ? "Collapse" : "Expand"}
          onClick={narrow ? () => setDrawer(false) : toggle}
          size={40}
          tip="none"
        />
        {wide && (
          <span className="flex items-center gap-2 pl-1">
            <Orb size={20} />
            <span className="font-display text-[17px] font-semibold tracking-tight text-ink">Jarvis</span>
          </span>
        )}
      </div>

      <div className="mt-4 space-y-0.5">
        <NavRow icon={SquarePen} label="New chat" open={wide} onClick={newChat} />
        {wide && query !== null ? (
          <div className="flex h-10 items-center gap-3 rounded-full bg-ink/[0.06] px-3">
            <Search size={19} strokeWidth={1.75} className="shrink-0 text-ink-faint" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Escape" && setQuery(null)}
              onBlur={() => query === "" && setQuery(null)}
              placeholder="Search chats"
              className="min-w-0 flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-ink-faint"
            />
          </div>
        ) : (
          <NavRow
            icon={Search}
            label="Search chats"
            open={wide}
            onClick={() => {
              if (!open) toggle();
              setQuery("");
            }}
          />
        )}
        <NavRow icon={ImageIcon} label="Images" open={wide} active={sheet === "images"} onClick={place("images")} />
        <NavRow icon={SquareTerminal} label="Code" open={wide} active={sheet === "code" || codeOn} onClick={place("code")} />
      </div>

      <div className="scroll-quiet mt-4 min-h-0 flex-1 overflow-y-auto">
        <AnimatePresence initial={false}>
          {open &&
            groups.map(([label, items]) => (
              <motion.section key={label} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="mb-3">
                <h3 className="px-3 pb-1 pt-2 text-[12px] font-medium text-ink-faint">{label}</h3>
                {items.map((c) => (
                  <ChatRow key={c.id} conversation={c} active={c.id === activeId} />
                ))}
              </motion.section>
            ))}
        </AnimatePresence>
        {wide && groups.length === 0 && query && (
          <p className="px-3 py-2 text-[13px] text-ink-faint">No chats match "{query}".</p>
        )}
      </div>

      <div className="space-y-0.5 pt-2">
        <UpdateRow open={wide} />
        <NavRow icon={House} label="Home" open={wide} active={sheet === "home"} onClick={place("home")} />
        <NavRow icon={Brain} label="Memory" open={wide} active={sheet === "memory"} onClick={place("memory")} />
        <NavRow icon={FolderCode} label="Files" open={wide} active={sheet === "files"} onClick={place("files")} />
        <NavRow icon={Library} label="Knowledge" open={wide} active={sheet === "knowledge"} onClick={place("knowledge")} />
        <NavRow icon={CandlestickChart} label="Trading" open={wide} active={sheet === "forecast"} onClick={place("forecast")} />
        <NavRow icon={Bot} label="Agents" open={wide} active={sheet === "agents"} badge={waiting} onClick={place("agents")} />
        <NavRow icon={Settings} label="Settings" open={wide} active={sheet === "settings"} onClick={place("settings")} />
      </div>
    </motion.aside>
    </>
  );
}
