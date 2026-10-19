// Files: a folder on the left, the open file in the middle - yours to edit - and Jarvis on the
// right, proposing changes you read as diffs before any of them touch the file.
import { FolderOpen, FolderPlus, Play, Save, Undo2, X } from "lucide-react";
import { useEffect, useState } from "react";
import Sheet from "../shell/Sheet";
import { useFiles } from "../store/files";
import { Button, Empty, FIELD, IconButton } from "../ui/controls";
import Changes from "./Changes";
import Tree from "./Tree";

interface Desktop {
  pywebview?: { api?: { pick_folder?: () => Promise<string | null> } };
}
const picker = () => (window as unknown as Desktop).pywebview?.api?.pick_folder;

function AddFolder() {
  const addRoot = useFiles((s) => s.addRoot);
  const [typing, setTyping] = useState("");
  const pick = picker();
  if (pick) {
    return (
      <Button small icon={FolderPlus} onClick={() => void pick().then((path) => (path ? addRoot(path) : undefined))}>
        Open folder
      </Button>
    );
  }
  // In a plain browser there is no native picker: type the path.
  return (
    <input
      value={typing}
      onChange={(e) => setTyping(e.target.value)}
      onKeyDown={(e) => e.key === "Enter" && typing.trim() && void addRoot(typing).then(() => setTyping(""))}
      placeholder="Folder path, then Enter"
      className={`${FIELD} !py-1.5 text-[13px]`}
    />
  );
}

function RunBar() {
  const { run, running, runCommand } = useFiles();
  const [command, setCommand] = useState("");
  return (
    <div className="mt-3 border-t border-ink/[0.06] pt-3">
      <div className="flex items-center gap-2">
        <input
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void runCommand(command)}
          placeholder="Run a command in this folder, e.g. pytest"
          className={`${FIELD} !py-1.5 font-mono text-[12.5px]`}
        />
        <Button small icon={Play} disabled={running || !command.trim()} onClick={() => void runCommand(command)}>
          {running ? "Running…" : "Run"}
        </Button>
      </div>
      {run && (
        <pre className="scroll-quiet mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-2xl bg-ink/[0.04] p-3 font-mono text-[11.5px] text-ink">
          <span className={run.exit_code === 0 ? "text-success" : "text-danger"}>
            $ {run.command} → exit {run.exit_code}
            {run.timed_out ? " (stopped after 5 minutes)" : ""} · {(run.elapsed_ms / 1000).toFixed(1)}s
          </span>
          {"\n"}
          {run.output || "(no output)"}
        </pre>
      )}
    </div>
  );
}

export default function FilesSheet() {
  const { roots, root, file, draft, refresh, pickRoot, closeRoot, setDraft, save, undo } = useFiles();
  useEffect(() => void refresh(), [refresh]);
  const dirty = file !== null && draft !== file.text;

  return (
    <Sheet title="Files" subtitle="Edit files yourself, or ask Jarvis and review every change before it is made." width={1280}>
      {roots.length === 0 ? (
        <Empty icon={FolderOpen} title="Open a folder">
          A code project or a folder of documents. Text, Markdown, code and Word files open here; nothing is changed until you
          save or apply.
          <div className="mt-4 flex justify-center">
            <AddFolder />
          </div>
        </Empty>
      ) : (
        <div className="flex h-[66vh] min-h-[420px] gap-4">
          <aside className="flex w-60 shrink-0 flex-col">
            <div className="mb-2 flex items-center gap-1">
              <select
                value={root ?? ""}
                onChange={(e) => void pickRoot(e.target.value)}
                className="min-w-0 flex-1 truncate rounded-xl bg-ink/[0.05] px-2 py-1.5 text-[13px] font-medium text-ink outline-none"
              >
                {roots.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
              {root && <IconButton icon={X} label="Close folder" size={30} onClick={() => void closeRoot(root)} />}
            </div>
            <Tree />
            <div className="pt-2">
              <AddFolder />
            </div>
          </aside>

          <section className="flex min-w-0 flex-1 flex-col">
            {file ? (
              <>
                <div className="mb-2 flex items-center gap-2">
                  <p className="min-w-0 flex-1 truncate font-mono text-[12.5px] text-ink-muted">{file.path}</p>
                  {file.can_undo && (
                    <Button small tone="ghost" icon={Undo2} onClick={() => void undo()}>
                      Undo last change
                    </Button>
                  )}
                  <Button small tone={dirty ? "primary" : "ghost"} icon={Save} disabled={!dirty} onClick={() => void save()}>
                    Save
                  </Button>
                </div>
                {file.note && <p className="mb-2 text-[12px] text-ink-faint">{file.note}</p>}
                <textarea
                  value={draft}
                  spellCheck={file.kind === "docx"}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                      e.preventDefault();
                      if (dirty) void save();
                    }
                  }}
                  className={`scroll-quiet min-h-0 flex-1 resize-none rounded-2xl border border-ink/[0.08] bg-ink/[0.02] p-4 text-ink outline-none ${
                    file.kind === "docx" ? "text-[14px] leading-relaxed" : "font-mono text-[12.5px] leading-relaxed"
                  }`}
                />
              </>
            ) : (
              <p className="pt-2 text-[13px] text-ink-faint">Pick a file on the left.</p>
            )}
            {root && <RunBar />}
          </section>

          <aside className="flex w-[380px] shrink-0 flex-col">
            <Changes />
          </aside>
        </div>
      )}
    </Sheet>
  );
}
