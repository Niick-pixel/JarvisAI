// The folder on the left: directories open in place, a file opens in the middle.
import { ChevronRight, File, FileText, Folder } from "lucide-react";
import type { FileEntry } from "../api/types";
import { useFiles } from "../store/files";

function Rows({ parent, depth }: { parent: string; depth: number }) {
  const entries = useFiles((s) => s.children[parent]) ?? [];
  const open = useFiles((s) => s.open);
  const current = useFiles((s) => s.file?.path);
  const toggle = useFiles((s) => s.toggle);
  return (
    <>
      {entries.map((entry: FileEntry) => {
        const Icon = entry.dir ? Folder : entry.name.endsWith(".docx") || entry.name.endsWith(".md") ? FileText : File;
        return (
          <div key={entry.path}>
            <button
              type="button"
              onClick={() => void toggle(entry)}
              style={{ paddingLeft: 8 + depth * 14 }}
              className={`flex h-8 w-full items-center gap-1.5 rounded-xl pr-2 text-left text-[13px] transition-colors ${
                current === entry.path ? "bg-accent/12 font-medium text-accent" : "text-ink hover:bg-ink/[0.05]"
              }`}
            >
              <ChevronRight
                size={14}
                className={`shrink-0 text-ink-faint transition-transform ${entry.dir ? "" : "invisible"} ${open[entry.path] ? "rotate-90" : ""}`}
              />
              <Icon size={15} strokeWidth={1.75} className="shrink-0 text-ink-muted" />
              <span className="truncate">{entry.name}</span>
            </button>
            {entry.dir && open[entry.path] && <Rows parent={entry.path} depth={depth + 1} />}
          </div>
        );
      })}
    </>
  );
}

export default function Tree() {
  return (
    <div className="scroll-quiet min-h-0 flex-1 overflow-y-auto py-1">
      <Rows parent="" depth={0} />
    </div>
  );
}
